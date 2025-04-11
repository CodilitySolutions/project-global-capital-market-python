import os
from dotenv import load_dotenv
import pymssql
from app.settings.logger import logger

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

server = os.getenv("DB_HOST")
database = os.getenv("DB_NAME")
username = os.getenv("DB_USER")
password = os.getenv("DB_PASS")

class Database:

    def __init__(self):
        self.conn = pymssql.connect(server, username, password, database, as_dict=True)

    def create_table(self):
        try:
            create_table_query = """
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
            logger.info("✅ Table created.")
        except pymssql.DatabaseError as e:
            logger.error(f"❌ Error creating table: {e}")

    def read_user_data(self):
        query = """
            SELECT accountid, country, city, address 
            FROM report.vtiger_account a 
            WHERE country IN ('South Africa') AND client_qualification_date > '2023-01-01 00:00:01' 
            AND accountid NOT IN (
                SELECT accountid 
                FROM [dbo].[client_location_cost] 
                WHERE modified_date IS NOT NULL
            );
        """
        cursor = self.conn.cursor()
        cursor.execute(query)
        records = cursor.fetchall()
        logger.info(f"📊 Client records fetched: {len(records)}")
        return records

    def read_property_sites_data(self, country, city, address):
        query = "SELECT STRING_AGG(property_sites.property_url, ' ') AS property_urls FROM dbo.property_sites WHERE country = %s"
        cursor = self.conn.cursor()
        cursor.execute(query, country)
        records = cursor.fetchall()
        return records[0]['property_urls']

    def read_client(self, accountid):
        query = "SELECT * FROM report.vtiger_account WHERE accountid = %s"
        cursor = self.conn.cursor()
        cursor.execute(query, accountid)
        return cursor.fetchone()

    def insert_data(self, data):
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) AS TOTAL FROM [dbo].[client_location_cost] WHERE accountid = %s", data[0][0])
        records = cursor.fetchall()

        if records[0]["TOTAL"] > 0:
            cursor.execute("SELECT client_neighborhood, street_cost_sqm FROM [dbo].[client_location_cost] WHERE accountid = %s", data[0][0])
            existing = cursor.fetchall()[0]

            if existing["client_neighborhood"] != data[0][1] or existing["street_cost_sqm"] != str(data[0][2]):
                query = f"""
                    UPDATE [dbo].[client_location_cost]
                    SET 
                        client_neighborhood = '{data[0][1]}',
                        street_cost_sqm = {data[0][2]},
                        object = '{data[0][3]}',
                        area_type = '{data[0][4]}',
                        street_people_type = '{data[0][5]}',
                        image_people_type = '{data[0][6]}',
                        property_type = '{data[0][6]}',
                        is_valid = {data[0][7]},
                        modified_date = GETDATE()
                    WHERE accountid = {data[0][0]};
                """
                cursor.execute(query)
                self.conn.commit()
                logger.info(f"📝 Client {data[0][0]} updated.")
            else:
                logger.info(f"⏭️ Client {data[0][0]} skipped (no changes).")
        else:
            query = """
                INSERT INTO [dbo].[client_location_cost] 
                (accountid, client_neighborhood, street_cost_sqm, object, area_type, street_people_type, property_type, is_valid, modified_date) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, GETDATE())
            """
            cursor.executemany(query, data)
            self.conn.commit()
            logger.info(f"➕ Client {data[0][0]} inserted.")
        cursor.close()

    def insert_cost(self, data):
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) AS TOTAL FROM [dbo].[client_location_cost] WHERE accountid = %s", data[0][0])
        records = cursor.fetchall()

        if records[0]["TOTAL"] > 0:
            query = f"""
                UPDATE [dbo].[client_location_cost]
                SET 
                    street_cost_sqm = {data[0][1]},
                    is_valid = {data[0][2]},
                    modified_date = GETDATE()
                WHERE accountid = {data[0][0]};
            """
            logger.debug(f"🧾 Update Query: {query}")
            cursor.execute(query)
            self.conn.commit()
            logger.info(f"📝 Cost updated for account {data[0][0]}")
        else:
            query = """
                INSERT INTO [dbo].[client_location_cost] 
                (accountid, street_cost_sqm, is_valid, modified_date) 
                VALUES (%s, %s, %s, GETDATE())
            """
            cursor.executemany(query, data)
            self.conn.commit()
            logger.info(f"➕ Cost inserted for account {data[0][0]}")
        cursor.close()

    def update_neighborhood_data(self, data):
        cursor = self.conn.cursor()
        query = f"UPDATE [dbo].[client_location_cost] SET client_neighborhood = '{data[0][1]}' WHERE accountid = {data[0][0]}"
        cursor.execute(query)
        self.conn.commit()
        cursor.close()
        logger.info(f"🏘️ Neighborhood updated for account {data[0][0]}")

    def update_cost_data(self, data):
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) AS TOTAL FROM [dbo].[client_location_cost] WHERE accountid = %s", data[0][0])
        records = cursor.fetchall()

        if records[0]["TOTAL"] > 0:
            logger.info(f"📝 Updating cost data for account {data[0][0]}")
            query = """
                UPDATE [dbo].[client_location_cost]
                SET 
                    neighborhood_cost_sqm = %s,
                    street_cost_sqm = %s,
                    build_cost_sqm = %s,
                    image_people_type = %s,
                    street_people_type = %s,
                    neighbourhood_people_type = %s,
                    object = %s,
                    area_type = %s,
                    property_type = %s,
                    is_valid = %s,
                    modified_date = GETDATE(),
                    client_neighborhood = %s,
                    people_type = %s
                WHERE accountid = %s;
            """

            params = (
                data[0][1], data[0][2], data[0][3], data[0][4], data[0][5],
                data[0][6], data[0][7], data[0][8], data[0][9], data[0][10],
                data[0][11], data[0][12], data[0][0]
            )

            logger.info(f"🧾 Update Query Params: {params}")
            cursor.execute(query, params)
            self.conn.commit()
            logger.info(f"♻️ Updated cost data for account {data[0][0]}")
        else:
            logger.info(f"➕ Inserting cost data for account {data[0][0]}")
            query = """INSERT INTO [dbo].[client_location_cost] 
                (accountid, neighborhood_cost_sqm, street_cost_sqm, build_cost_sqm, image_people_type, 
                street_people_type, neighbourhood_people_type, object, area_type, property_type, 
                is_valid, modified_date, client_neighborhood, people_type) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, GETDATE(), %s, %s);"""

            params = (
                data[0][0], data[0][1], data[0][2], data[0][3], data[0][4],
                data[0][5], data[0][6], data[0][7], data[0][8], data[0][9],
                data[0][10], data[0][11], data[0][12]
            )

            cursor.execute(query, params)
            self.conn.commit()
            logger.info(f"➕ Inserted cost data for account {data[0][0]}")
        cursor.close()

    def read_cost_data(self):
        query = "SELECT * FROM [dbo].[client_location_cost] WHERE client_neighborhood = '';"
        cursor = self.conn.cursor()
        cursor.execute(query)
        records = cursor.fetchall()
        logger.info(f"📥 Found {len(records)} records with missing neighborhoods.")
        return records

    def remove_duplicate_records(self):
        query = "SELECT accountid, COUNT(*) AS RecordCount FROM [dbo].[client_location_cost] GROUP BY accountid;"
        cursor = self.conn.cursor()
        cursor.execute(query)
        records = cursor.fetchall()

        for record in records:
            if record['RecordCount'] > 1:
                cursor.execute("DELETE FROM [dbo].[client_location_cost] WHERE accountid = %s", record['accountid'])
                self.conn.commit()
                logger.warning(f"❌ Duplicate record removed for account {record['accountid']}")
        cursor.close()

    def get_fields(self, table_name):
        query = f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = {table_name}"
        cursor = self.conn.cursor()
        cursor.execute(query)
        records = cursor.fetchall()
        logger.info(f"📋 Fields for table '{table_name}': {records}")
        return records
