import os
from dotenv import load_dotenv
import pymssql

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, "dot.env"))

server = os.getenv("DB_HOST")
database = os.getenv("DB_NAME")
username = os.getenv("DB_USER")
password = os.getenv("DB_PASS")

class Database:

    def __init__(self):
        self.conn = pymssql.connect(server, username, password, database, as_dict=True)

    def create_table(self):
        try:
            create_table_query="""
                CREATE TABLE report.address_cost (
                ID INT IDENTITY(1,1) PRIMARY KEY,
                cost_per_meter_square INT NOT NULL,
                address varchar(255),
                accountid INT,
                CONSTRAINT FK_accountid FOREIGN KEY (accountid) REFERENCES report.vtiger_account(accountid) ON DELETE CASCADE)
            """
            cursor = self.conn.cursor()
            cursor.execute(create_table_query)
            self.conn.commit()

            print("Table created.")

        except pymssql.DatabaseError as e:
            print("Error:", e)

    def read_user_data(self):
        query="""select accountid, country, city, address from report.vtiger_account a 
            where country IN ('South Africa', 'Nigeria') AND address='ugbuwangue' AND client_qualification_date>'2024-01-01 00:00:01';
        """
        # and not exists (select 1 from [dbo].[client_location_cost] b WHERE a.accountid = b.accountid);

        cursor = self.conn.cursor()
        cursor.execute(query)

        records = cursor.fetchall()
        print("Client records: ", len(records))
        return records

    def read_client(self, accountid):
        query = "SELECT * FROM report.vtiger_account WHERE accountid = %s"
        cursor = self.conn.cursor()
        cursor.execute(query, accountid)

        record = cursor.fetchone()
        return record

    def insert_data(self, data):
        cursor = self.conn.cursor()
        query = "SELECT COUNT(*) AS TOTAL FROM [dbo].[client_location_cost] WHERE accountid = %s"
        cursor.execute(query, data[0][0])
        records = cursor.fetchall()

        if records[0]["TOTAL"] > 0:
            query = "SELECT client_neighborhood, street_cost_sqm FROM [dbo].[client_location_cost] WHERE accountid = %s"
            cursor.execute(query, data[0][0])
            records = cursor.fetchall()

            print('records[0]["street_cost_sqm"] : ', records[0]["street_cost_sqm"] )
            print('records[0]["client_neighborhood"]: ', records[0]["client_neighborhood"])

            if records[0]["client_neighborhood"] != data[0][1] or records[0]["street_cost_sqm"] != str(data[0][2]):
                query = f"UPDATE [dbo].[client_location_cost] SET client_neighborhood='{data[0][1]}', street_cost_sqm={data[0][2]}, object='{data[0][3]}', area_type='{data[0][4]}', street_people_type='{data[0][5]}', property_type='{data[0][6]}', is_valid={data[0][7]} WHERE accountid = {data[0][0]};"
                cursor.execute(query)
                self.conn.commit()
                print("Client updated")
            else:
                print("Client skipped")
        else:
            query = "INSERT INTO [dbo].[client_location_cost] (accountid, client_neighborhood, street_cost_sqm, object, area_type, street_people_type, property_type, is_valid) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
            cursor.executemany(query, data)
            self.conn.commit()
            print("Client inserted")
        cursor.close()

    def insert_cost(self, data):
        cursor = self.conn.cursor()
        query = "SELECT COUNT(*) AS TOTAL FROM [dbo].[client_location_cost] WHERE accountid = %s"
        cursor.execute(query, data[0][0])
        records = cursor.fetchall()

        if records[0]["TOTAL"] > 0:
            query = f"UPDATE [dbo].[client_location_cost] SET street_cost_sqm={data[0][1]}, is_valid={data[0][2]} WHERE accountid = {data[0][0]};"
            cursor.execute(query)
            self.conn.commit()
            print("Cost updated")
        else:
            query = "INSERT INTO [dbo].[client_location_cost] (accountid, street_cost_sqm, is_valid) VALUES (%s, %s, %s)"
            cursor.executemany(query, data)
            self.conn.commit()
            print("Cost inserted")

        cursor.close()

    def update_neighborhood_data(self, data):
        cursor = self.conn.cursor()

        query = f"UPDATE [dbo].[client_location_cost] SET client_neighborhood='{data[0][1]}' WHERE accountid = {data[0][0]};"
        cursor.execute(query)
        self.conn.commit()
        cursor.close()

        print("Neighborhood updated")

    def update_cost_data(self, data):
        cursor = self.conn.cursor()
        query = f"UPDATE [dbo].[client_location_cost] SET neighborhood_cost_sqm='{data[0][1]}', street_cost_sqm='{data[0][2]}', build_cost_sqm='{data[0][3]}', image_people_type='{data[0][4]}', street_people_type='{data[0][5]}', neighbourhood_people_type='{data[0][6]}' WHERE accountid = {data[0][0]};"
        cursor.execute(query)
        self.conn.commit()
        cursor.close()

        print("Client updated")

    def read_cost_data(self):
        # query = """SELECT COUNT(*) AS TOTAL FROM [dbo].[client_location_cost]"""
        # query = """SELECT * FROM [dbo].[client_location_cost]"""
        query = """SELECT * FROM [dbo].[client_location_cost] WHERE client_neighborhood='';"""

        cursor = self.conn.cursor()
        cursor.execute(query)

        records = cursor.fetchall()
        print('records: ', len(records))

        # for record in records:
        #     print('record: ', record["street_people_type"], record["area_type"], record["is_valid"])

        return records

    def remove_duplicate_records(self):
        query = """SELECT accountid, COUNT(*) AS RecordCount FROM [dbo].[client_location_cost] GROUP BY accountid;"""

        cursor = self.conn.cursor()
        cursor.execute(query)

        records = cursor.fetchall()

        for record in records:
            if record['RecordCount'] > 1:
                query = """DELETE FROM [dbo].[client_location_cost] WHERE accountid = %s;"""
                cursor.execute(query, record['accountid'])
                self.conn.commit()
                print('Deleted record: ', record['accountid'])

    def get_fields(self, table_name):
        query = f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = {table_name}"
        cursor = self.conn.cursor()
        cursor.execute(query)

        records = cursor.fetchall()
        print('records: ', records)

# db = Database()
# db.read_user_data()
# db.read_cost_data()
# db.get_fields('client_location_cost')
# db.remove_duplicate_records()