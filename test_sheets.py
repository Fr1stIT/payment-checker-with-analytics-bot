import asyncio
import asyncpg
import gspread
from gspread_formatting import CellFormat, Color, TextFormat, format_cell_range

class GoogleSheetUpdater:
    def __init__(self, db_params, credentials_file, sheet_name):
        self.db_params = db_params
        self.credentials_file = credentials_file
        self.sheet_name = sheet_name
        self.gc = gspread.service_account(filename=self.credentials_file)
        self.sheet = self.gc.open(self.sheet_name).sheet1

    async def get_database_data(self):
        conn = await asyncpg.connect(**self.db_params)
        query = """
            WITH order_totals AS (
                SELECT
                    orders.who_added AS user_id,
                    COUNT(orders.id) AS total_sales_count,
                    SUM(CASE WHEN template_orders.type = 'product' THEN orders.cost ELSE 0 END) AS product_sales,
                    SUM(CASE WHEN template_orders.type = 'service' THEN orders.cost ELSE 0 END) AS service_sales,
                    SUM(orders.cost) AS total_sales
                FROM orders
                JOIN template_orders ON orders.name = template_orders.name
                GROUP BY orders.who_added
            ),
            salary_totals AS (
                SELECT
                    salary.user_id,
                    SUM(salary.salary_product) AS salary_product_total,
                    SUM(salary.salary_service) AS salary_service_total,
                    SUM(salary.salary_product + salary.salary_service) AS employee_revenue,
                    SUM(CASE WHEN salary.sell_type = 'cash' THEN salary.salary_product + salary.salary_service ELSE 0 END) AS cash_sales,
                    SUM(CASE WHEN salary.sell_type = 'card' THEN salary.salary_product + salary.salary_service ELSE 0 END) AS card_sales
                FROM salary
                GROUP BY salary.user_id
            )
            SELECT
                users.user_id,
                users.user_name,
                CASE WHEN users.online THEN 'Онлайн' ELSE 'Офлайн' END AS online_status,
                COALESCE(order_totals.total_sales_count, 0) AS total_sales_count,
                COALESCE(order_totals.product_sales, 0) AS product_sales,
                COALESCE(order_totals.service_sales, 0) AS service_sales,
                COALESCE(order_totals.total_sales, 0) AS total_sales,
                COALESCE(salary_totals.employee_revenue, 0) AS employee_revenue,
                COALESCE(salary_totals.cash_sales, 0) AS cash_sales,
                COALESCE(salary_totals.card_sales, 0) AS card_sales
            FROM users
            LEFT JOIN order_totals ON users.user_id = order_totals.user_id
            LEFT JOIN salary_totals ON users.user_id = salary_totals.user_id;
        """
        data = await conn.fetch(query)
        await conn.close()
        return data

    async def get_sheet_data(self):
        data = self.sheet.get_all_values()
        headers = data[0]
        values = data[1:]
        return headers, values

    async def update_headers(self):
        header_values = [
            ['🚀 Номер сотрудника', '😊 Имя сотрудника', '📶 Статус', '🔢 Количество всех продаж', '💲 Сумма продаж товаров',
             '💼 Сумма продаж услуг', '💰 Общая сумма продаж', '💵💳 Выручка сотрудника', '💵 Выручка наличными', '💳 Выручка по картам']]
        self.sheet.update(values=header_values, range_name='A1:J1')

        header_format = CellFormat(
            backgroundColor=Color(0.0157, 0.137, 0.180),  # #04232e
            textFormat=TextFormat(bold=True, foregroundColor=Color(1, 1, 1), fontFamily='Century Gothic', fontSize=10),
            horizontalAlignment='CENTER'  # Выровнять по центру
        )
        format_cell_range(self.sheet, 'A1:J1', header_format)

    async def update_google_sheet(self, headers, sheet_data, db_data):
        sheet_data_dict = {row[0]: row for row in sheet_data}  # Преобразуем данные из Google Таблицы в словарь
        db_data_dict = {str(row[0]): row for row in db_data}  # Преобразуем данные из БД в словарь

        if sheet_data and sheet_data[-1][0] == 'Итого':
            self.sheet.delete_rows(len(sheet_data) + 1)

        for key, db_row in db_data_dict.items():
            if key in sheet_data_dict:
                sheet_row = sheet_data_dict[key]
                if sheet_row[1:] != list(map(str, db_row[1:])):
                    await self.update_row(headers, db_row, sheet_row[0])
            else:
                new_row = [str(item) for item in db_row]
                self.sheet.append_row(new_row)
                new_row_index = len(self.sheet.get_all_values())
                await self.apply_style_to_row(new_row_index, new_row[2])

        await self.add_totals_row()

    async def update_row(self, headers, db_row, sheet_row_id):
        cell = self.sheet.find(sheet_row_id)
        if cell:
            row_values = [str(item) for item in db_row]
            col_limit = min(len(headers), 10)
            range_name = f"A{cell.row}:J{cell.row}"
            self.sheet.update(values=[row_values[:col_limit]], range_name=range_name)
            await self.apply_style_to_row(cell.row, db_row[2])

    async def apply_style_to_row(self, row, status):
        dark_background = CellFormat(
            backgroundColor=Color(0.92, 0.92, 0.92),
            textFormat=TextFormat(fontFamily='Century Gothic', fontSize=10),
            horizontalAlignment='CENTER'
        )
        light_background = CellFormat(
            backgroundColor=Color(0.95, 0.95, 0.95),
            textFormat=TextFormat(fontFamily='Century Gothic', fontSize=10),
            horizontalAlignment='CENTER'
        )
        online_format = CellFormat(
            textFormat=TextFormat(fontFamily='Century Gothic', fontSize=10, foregroundColor=Color(0.0, 0.467, 0.514),
                                  bold=True)
        )
        offline_format = CellFormat(
            textFormat=TextFormat(fontFamily='Century Gothic', fontSize=10, foregroundColor=Color(0.608, 0.122, 0.290),
                                  bold=True)
        )

        format_cell_range(self.sheet, f"A{row}:J{row}", dark_background if row % 2 != 0 else light_background)
        if status == "Онлайн":
            format_cell_range(self.sheet, f"C{row}:C{row}", online_format)
        elif status == "Офлайн":
            format_cell_range(self.sheet, f"C{row}:C{row}", offline_format)

    async def add_totals_row(self):
        all_values = self.sheet.get_all_values()
        row_count = len(all_values)

        total_sales_count = 0
        total_product_sales = 0
        total_service_sales = 0
        total_sales = 0
        total_employee_revenue = 0
        total_cash_sales = 0
        total_card_sales = 0
        online_count = 0
        offline_count = 0

        for row in all_values[1:]:
            total_sales_count += int(row[3])
            total_product_sales += int(row[4])
            total_service_sales += int(row[5])
            total_sales += int(row[6])
            total_employee_revenue += int(row[7])
            total_cash_sales += int(row[8])
            total_card_sales += int(row[9])
            if row[2] == 'Онлайн':
                online_count += 1
            elif row[2] == 'Офлайн':
                offline_count += 1

        total_row = ['Итого', f'Всего сотрудников: {online_count + offline_count}',
                     f'Онлайн: {online_count}, Офлайн: {offline_count}', total_sales_count, total_product_sales,
                     total_service_sales, total_sales, total_employee_revenue, total_cash_sales, total_card_sales]
        self.sheet.append_row(total_row)

        total_format = CellFormat(
            backgroundColor=Color(0.8, 0.8, 0.8),
            textFormat=TextFormat(bold=True, fontFamily='Century Gothic', fontSize=10),
            horizontalAlignment='CENTER'
        )
        format_cell_range(self.sheet, f"A{row_count + 1}:J{row_count + 1}", total_format)

    async def update_sheet(self):
        headers, sheet_data = await self.get_sheet_data()
        expected_headers = ['🚀 Номер сотрудника', '😊 Имя сотрудника', '📶 Статус', '🔢 Количество всех продаж',
                            '💲 Сумма продаж товаров', '💼 Сумма продаж услуг', '💰 Общая сумма продаж', '💵💳 Выручка сотрудника',
                            '💵 Выручка наличными', '💳 Выручка по картам']
        if headers != expected_headers:
            await self.update_headers()
            headers = expected_headers

        db_data = await self.get_database_data()
        await self.update_google_sheet(headers, sheet_data, db_data)
        print("Данные успешно обновлены в Google Таблице.")

db_params = {
    'database': 'Employe',
    'user': 'postgres',
    'password': '7292',
    'host': 'localhost',
    'port': '5432'
}

updater = GoogleSheetUpdater(db_params, 'third-adminbot-export-sheets-135f85f904d3.json', 'test_analyt')

async def scheduled_task():
    await updater.update_sheet()


if __name__ == '__main__':
    asyncio.run(scheduled_task())
