from flask import Flask, request, send_file, jsonify
import mysql.connector
import os
import base64
from flask_cors import CORS

ID = 0
app = Flask(__name__)
CORS(app)
UPLOAD_FOLDER = 'ImageOutputs'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

try:
    MyDB = mysql.connector.connect(
        "host" = "utb1p8.stackhero-network.com",
        "user" = "root",
        "passwd" = "fMpWmSfSZiahU2ii0fbfTMne3kb7ZKie",
        "database" = "Images",
        "port" = "5622",
       "raise_on_warnings": True,
       "autocommit": True,
       "pool_reset_session": True
    )
try:
    connection_pool = mysql.connector.pooling.MySQLConnectionPool(**MyDB)
except mysql.connector.Error as err:
    print(f"Error creating connection pool: {err}")
    raise

def get_db_connection():
    try:
        connection = connection_pool.get_connection()
        connection.ping(reconnect=True, attempts=3, delay=5)
        return connection
    except mysql.connector.Error as err:
        print(f"Error getting connection from pool: {err}")
        raise


    MyCursor = MyDB.cursor()
    MyCursor.execute("""
        CREATE TABLE IF NOT EXISTS Images (
            id INTEGER(45) NOT NULL AUTO_INCREMENT PRIMARY KEY,
            file_name VARCHAR(255) NOT NULL,
            Photo LONGBLOB NOT NULL
        )
    """)
    MyCursor.execute("""
            CREATE TABLE IF NOT EXISTS Scores (
                id INTEGER(45) NOT NULL AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(255) NOT NULL UNIQUE,
                score INTEGER(11) NOT NULL
            )
      """)
    MyCursor.execute("""
            CREATE TABLE IF NOT EXISTS Login (
                id INTEGER(45) NOT NULL AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(255) NOT NULL,
                email VARCHAR(255) NOT NULL
            )
      """)
except mysql.connector.Error as e:
    print(f"Database connection or setup failed: {str(e)}")

def InsertBlob(FilePath, FileName):
    try:
        with open(FilePath, "rb") as File:
            BinaryData = File.read()
        SQLStatement = "INSERT INTO Images (file_name, Photo) VALUES (%s, %s)"
        MyCursor.execute(SQLStatement, (FileName, BinaryData))
        MyDB.commit()
    except mysql.connector.Error as e:
        print(f"Failed to insert blob: {str(e)}")

def RetrieveBlob(ID):
    try:
        SQLStatement2 = "SELECT * FROM Images WHERE id = %s"
        MyCursor.execute(SQLStatement2, (ID,))
        MyResult = MyCursor.fetchone()
        if MyResult:
            StoreFilePath = os.path.join(UPLOAD_FOLDER, MyResult[1])
            with open(StoreFilePath, "wb") as File:
                File.write(MyResult[2])
            return StoreFilePath
        else:
            return None
    except mysql.connector.Error as e:
        print(f"Failed to retrieve blob: {str(e)}")
        return None
def InsertScore(username, score):
    try:
        SQLStatement = "INSERT INTO Scores (username, score) VALUES (%s, %s)"
        MyCursor.execute(SQLStatement, (username, score))
        MyDB.commit()
        print("Score inserted successfully.")
    except mysql.connector.IntegrityError as e:
        if "Duplicate entry" in str(e) and "username" in str(e):
            print("Error: Username already exists. Please use a unique username.")
        else:
            print(f"Failed to insert score: {str(e)}")
    except mysql.connector.Error as e:
        print(f"Failed to insert score: {str(e)}")

def RetrieveScore(username):
    """Retrieve a user's score with proper error handling."""
    try:
        SQLStatement = "SELECT username, score FROM Scores WHERE username = %s"
        MyCursor.execute(SQLStatement, (username,))
        result = MyCursor.fetchone()
        if result:
            return {'username': result[0], 'score': result[1]}
        return None
    except mysql.connector.Error as e:
        print(f"Failed to retrieve score: {str(e)}")
        return None
def UpsertScore(username, score):
    """Insert or update a user's score."""
    try:
        # Try to update first
        SQLStatement = """
            INSERT INTO Scores (username, score) 
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE score = VALUES(score)
        """
        MyCursor.execute(SQLStatement, (username, score))
        MyDB.commit()
        return True
    except mysql.connector.Error as e:
        print(f"Failed to upsert score: {str(e)}")
        MyDB.rollback()
        return False
def InsertLogin(username, email):
    try:
        SQLStatement = "INSERT INTO Login (username, email) VALUES (%s, %s)"
        MyCursor.execute(SQLStatement, (username, email))
        MyDB.commit()
        print("Username inserted successfully.")
    except mysql.connector.IntegrityError as e:
        if "Duplicate entry" in str(e) and "username" in str(e):
            print("Error: Username already exists. Please use a unique username.")
        else:
            print(f"Failed to insert score: {str(e)}")
    except mysql.connector.Error as e:
        print(f"Failed to insert score: {str(e)}")

def RetrieveLogin(email):
    try:
        SQLStatement = "SELECT username FROM Login WHERE email = %s"
        MyCursor.execute(SQLStatement, (email,))
        result = MyCursor.fetchone()
        if result:
            return { 'username': result[0]}
        else:
            print("Login not found.")
            return None
    except mysql.connector.Error as e:
        print(f"Failed to retrieve login: {str(e)}")
        return None

@app.route('/insert_image', methods=['POST'])
def insert_image():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    file_name = file.filename
    binary_data = file.read()

    try:
        SQLStatement = "INSERT INTO Images (file_name, Photo) VALUES (%s, %s)"
        MyCursor.execute(SQLStatement, (file_name, binary_data))
        MyDB.commit()
        new_id = MyCursor.lastrowid
        return jsonify({'message': 'Image inserted successfully', 'id': new_id, 'file_name': file_name}), 200
    except mysql.connector.Error as e:
        return jsonify({'error': f'Failed to save the image: {str(e)}'}), 500

@app.route('/retrieve_image/<int:id>', methods=['GET'])
def retrieve_image(id):
    try:
        image_path = RetrieveBlob(id)
        if image_path:
            return send_file(image_path, mimetype='image/jpeg')
        else:
            return jsonify({'error': 'Image not found'}), 404
    except Exception as e:
        return jsonify({'error': f'Failed to retrieve image: {str(e)}'}), 500

@app.route('/delete_image/<int:id>', methods=['DELETE'])
def delete_image(id):
    try:
        SQLStatementCheck = "SELECT * FROM Images WHERE id = %s"
        MyCursor.execute(SQLStatementCheck, (id,))
        result = MyCursor.fetchone()

        if not result:
            return jsonify({'error': 'Image not found'}), 404

        SQLStatementDelete = "DELETE FROM Images WHERE id = %s"
        MyCursor.execute(SQLStatementDelete, (id,))
        MyDB.commit()
        
        return jsonify({'message': 'Image deleted successfully'}), 200
    except mysql.connector.Error as e:
        return jsonify({'error': f'Failed to delete image: {str(e)}'}), 500

@app.route('/retrieve_all_images', methods=['GET'])
def retrieve_all_images():
    try:
        SQLStatement = "SELECT id, Photo From Images"
        MyCursor.execute(SQLStatement)
        Result = MyCursor.fetchall()
        imagesAndIds = []
        for row in Result:
            image_id = row[0]
            photo = base64.b64encode(row[1]).decode('utf-8')
            imagesAndIds.append({'id': image_id, 'photo': photo})
        return jsonify(imagesAndIds), 200
    except mysql.connector.Error as e:
        return jsonify({'error': f'Failed to retrieve images: {str(e)}'}), 500

@app.route('/delete_all_images', methods=['DELETE'])
def delete_all_images():
    try:
        SQLStatement = "DELETE FROM Images"
        MyCursor.execute(SQLStatement)
        MyDB.commit()
        return jsonify({'message': 'All images deleted successfully'}), 200
    except mysql.connector.Error as err:
        MyDB.rollback() 
        return jsonify({'error': f'Failed to delete images: {str(err)}'}), 500

@app.route('/GrabImageForGuessing', methods=['GET'])
def grab_image_for_guessing():
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
      
        count_query = "SELECT COUNT(*) as count FROM Images"
        cursor.execute(count_query)
        count_result = cursor.fetchone()
        
        if not count_result or count_result['count'] == 0:
            return jsonify({"error": "No images available"}), 404
            
        query = "SELECT id, file_name, Photo FROM Images ORDER BY RAND() LIMIT 1"
        cursor.execute(query)
        result = cursor.fetchone()
        
        if not result:
            return jsonify({"error": "No images available"}), 404
            
       
        photo_base64 = base64.b64encode(result['Photo']).decode('utf-8')
        
        return jsonify({
            "id": result['id'],
            "file_name": result['file_name'],
            "photo": photo_base64
        }), 200
        
    except mysql.connector.Error as err:
        print(f"Database error in grab_image_for_guessing: {err}")
        return jsonify({"error": str(err)}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

@app.route('/AmountOfImages', methods=['GET'])
def amount_of_images():
    try:
        SQLStatement = "SELECT COUNT(*) FROM Images"
        MyCursor.execute(SQLStatement)
        result = MyCursor.fetchone()
        return jsonify({'count': result[0]}), 200
    except mysql.connector.Error as err:
        return jsonify({'error': f'Failed to retrieve amount of images: {str(err)}'}), 500


@app.route('/insert_score', methods=['POST'])
def insert_score():
    connection = None
    cursor = None
    try:
        data = request.get_json()
        if not data or 'username' not in data or 'score' not in data:
            return jsonify({"error": "Missing required fields"}), 400

        connection = get_db_connection()
        cursor = connection.cursor()

        
        check_query = "SELECT username FROM Login WHERE username = %s"
        cursor.execute(check_query, (data['username'],))
        if not cursor.fetchone():
            return jsonify({"error": "User does not exist"}), 404

        connection.start_transaction()
        
        query = """
            REPLACE INTO Scores (username, score)
            VALUES (%s, %s)
        """
        cursor.execute(query, (data['username'], data['score']))
        connection.commit()

        return jsonify({
            "message": "Score updated successfully",
            "username": data['username'],
            "score": data['score']
        }), 200

    except mysql.connector.Error as err:
        if connection:
            connection.rollback()
        print(f"Database error in insert_score: {err}")
        return jsonify({"error": str(err)}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
@app.route('/retrieve_score/<string:username>', methods=['GET'])
def retrieve_score(username):
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        query = "SELECT username, score FROM Scores WHERE username = %s"
        cursor.execute(query, (username,))
        result = cursor.fetchone()
        
        if result:
            return jsonify(result), 200
        return jsonify({"message": "Score not found"}), 404
        
    except mysql.connector.Error as err:
        print(f"Database error in retrieve_score: {err}")
        return jsonify({"error": str(err)}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
@app.route('/retrieve_all_scores', methods=['GET'])
def retrieve_all_scores():
    try:
        SQLStatement = "SELECT id, username, score FROM Scores"
        MyCursor.execute(SQLStatement)
        Result = MyCursor.fetchall()
        
        scores_list = []
        for row in Result:
            score_data = {
                'id': row[0],
                'username': row[1],
                'score': row[2]
            }
            scores_list.append(score_data)
        
        return jsonify(scores_list), 200
    except mysql.connector.Error as e:
        return jsonify({'error': f'Failed to retrieve scores: {str(e)}'}), 500

@app.route('/delete_all_scores', methods=['DELETE'])
def delete_all_scores():
    try:
        SQLStatement = "DELETE FROM Scores"
        MyCursor.execute(SQLStatement)
        MyDB.commit()
        
        return jsonify({'message': 'All scores deleted successfully'}), 200
    except mysql.connector.Error as e:
        MyDB.rollback() 
        return jsonify({'error': f'Failed to delete scores: {str(e)}'}), 500
@app.route('/update_score', methods=['PUT'])
def update_score():
    try:
        data = request.get_json()
        if not data or 'username' not in data or 'score' not in data:
            return jsonify({
                'error': 'Missing required fields',
                'message': 'Username and score are required'
            }), 400

        username = data['username']
        score = data['score']

        if UpsertScore(username, score):
            return jsonify({
                'message': 'Score updated successfully',
                'username': username,
                'score': score
            }), 200
        else:
            return jsonify({
                'error': 'Database operation failed',
                'message': 'Failed to update score'
            }), 500
    except Exception as e:
        return jsonify({
            'error': str(e),
            'message': 'Internal server error while updating score'
        }), 500
@app.route('/insert_login', methods=['POST'])
def insert_login():
    connection = None
    cursor = None
    try:
        data = request.get_json()
        if not data or 'username' not in data or 'email' not in data:
            return jsonify({"error": "Missing required fields"}), 400

        connection = get_db_connection()
        cursor = connection.cursor()

       
        check_query = "SELECT username FROM Login WHERE email = %s"
        cursor.execute(check_query, (data['email'],))
        existing_user = cursor.fetchone()

        if existing_user:
            return jsonify({"message": "User already exists"}), 200

      
        connection.start_transaction()
        
        insert_query = "INSERT INTO Login (username, email) VALUES (%s, %s)"
        cursor.execute(insert_query, (data['username'], data['email']))
        

        score_query = "INSERT INTO Scores (username, score) VALUES (%s, 0)"
        cursor.execute(score_query, (data['username'],))
        
        connection.commit()
        return jsonify({"message": "User registered successfully"}), 200

    except mysql.connector.Error as err:
        if connection:
            connection.rollback()
        print(f"Database error in insert_login: {err}")
        return jsonify({"error": str(err)}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
    

@app.route('/retrieve_login/<string:email>', methods=['GET'])
def retrieve_login(email):
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        query = "SELECT username, email FROM Login WHERE email = %s"
        cursor.execute(query, (email,))
        result = cursor.fetchone()
        
        if result:
            return jsonify(result), 200
        return jsonify({"message": "User not found"}), 404
        
    except mysql.connector.Error as err:
        print(f"Database error in retrieve_login: {err}")
        return jsonify({"error": str(err)}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
@app.route('/retrieve_all_logins', methods=['GET'])
def retrieve_all_logins():
    try:
        SQLStatement = "SELECT id, username, email FROM Login"
        MyCursor.execute(SQLStatement)
        Result = MyCursor.fetchall()
        
        login_list = []
        for row in Result:
            login_data = {
                'id': row[0],
                'username': row[1],
                'email': row[2]
            }
            login_list.append(login_data)
        
        return jsonify(login_list), 200
    except mysql.connector.Error as e:
        return jsonify({'error': f'Failed to retrieve logins: {str(e)}'}), 500
@app.route('/delete_all_logins', methods=['DELETE'])
def delete_all_logins():
    try:
        SQLStatement = "DELETE FROM Login"
        MyCursor.execute(SQLStatement)
        MyDB.commit()
        
        return jsonify({'message': 'All logins deleted successfully'}), 200
    except mysql.connector.Error as e:
        MyDB.rollback() 
        return jsonify({'error': f'Failed to delete logins: {str(e)}'}), 500


if __name__ == '__main__':
    try:
        app.run(host='0.0.0.0', port=5000, debug=True)
    except Exception as e:
        print(f"Failed to start the server: {str(e)}")
