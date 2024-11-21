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
        host = "utb1p8.stackhero-network.com",
        user = "root",
        passwd = "fMpWmSfSZiahU2ii0fbfTMne3kb7ZKie",
        database = "Images",
        port = "5622",
        pool_name="mypool",
        pool_size=5,
        autocommit=True
    )

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

def RetrieveScore(user_id):
    try:
        SQLStatement = "SELECT username, score FROM Scores WHERE id = %s"
        MyCursor.execute(SQLStatement, (user_id,))
        result = MyCursor.fetchone()
        if result:
            return {'id': user_id, 'username': result[0], 'score': result[1]}
        else:
            print("Score not found.")
            return None
    except mysql.connector.Error as e:
        print(f"Failed to retrieve score: {str(e)}")
        return None
def InsertLogin(username, email):
    try:
        SQLStatement = "INSERT INTO Login (username, email) VALUES (%s, %s)"
        MyCursor.execute(SQLStatement, (username, email))
        MyDB.commit()
        print("Score inserted successfully.")
    except mysql.connector.Error as e:
        print(f"Failed to insert score: {str(e)}")
def RetrieveLogin(user_id):
    try:
        SQLStatement = "SELECT username, email FROM Login WHERE id = %s"
        MyCursor.execute(SQLStatement, (user_id,))
        result = MyCursor.fetchone()
        if result:
            return {'id': user_id, 'username': result[0], 'email': result[1]}
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
def retrieve_image_for_guessing():
    try:
        SQLStatement = "SELECT id, Photo FROM Images ORDER BY RAND() LIMIT 1"
        MyCursor.execute(SQLStatement) 
        result = MyCursor.fetchone()
        
        if not result:
            return jsonify({'error': 'No images found'}), 404
        
        image_id = result[0]
        photo = base64.b64encode(result[1]).decode('utf-8')
        
        return jsonify({'id': image_id, 'photo': photo}), 200
    except mysql.connector.Error as err:
        return jsonify({'error': f'Failed to retrieve image: {str(err)}'}), 500

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
    data = request.get_json()
    username = data.get('username')
    score = data.get('score')

    if not username or score is None:
        return jsonify({'error': 'Username and score are required'}), 400

    try:
        InsertScore(username, score)
        return jsonify({'message': 'Score inserted successfully', 'username': username, 'score': score}), 200
    except mysql.connector.IntegrityError as e:
        if "Duplicate entry" in str(e) and "username" in str(e):
            return jsonify({'error': 'Username already exists. Please choose a different username.'}), 409
        return jsonify({'error': f'Failed to insert score: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': f'Failed to insert score: {str(e)}'}), 500

@app.route('/retrieve_score/<int:user_id>', methods=['GET'])
def retrieve_score(user_id):
    try:
        score_data = RetrieveScore(user_id)
        if score_data:
            return jsonify(score_data), 200
        else:
            return jsonify({'error': 'Score not found'}), 404
    except Exception as e:
        return jsonify({'error': f'Failed to retrieve score: {str(e)}'}), 500
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
@app.route('/insert_login', methods=['POST'])
def insert_login():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')

    if not username or email is None:
        return jsonify({'error': 'Username and email are required'}), 400

    try:
        InsertLogin(username, email)
        return jsonify({'message': 'Login inserted successfully', 'username': username, 'email': email}), 200
    except Exception as e:
        return jsonify({'error': f'Failed to insert login: {str(e)}'}), 500
@app.route('/retrieve_login/<int:user_id>', methods=['GET'])
def retrieve_login(user_id):
    try:
        login_data = RetrieveLogin(user_id)
        if login_data:
            return jsonify(login_data), 200
        else:
            return jsonify({'error': 'Login not found'}), 404
    except Exception as e:
        return jsonify({'error': f'Failed to retrieve login: {str(e)}'}), 500
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

@app.route('/retrieve_userID/<string:email>', methods=['GET'])
def retrieve_userID(email):
    try:
        SQLStatement = "SELECT id FROM Login WHERE email = %s"
        MyCursor.execute(SQLStatement, (email,))
        result = MyCursor.fetchone()
        if result:
            return jsonify({'id': result[0]}), 200
        else:
            return jsonify({'error': 'User not found'}), 404
    except mysql.connector.Error as e:
        return jsonify({'error': f'Failed to retrieve user: {str(e)}'}), 500
    


if __name__ == '__main__':
    try:
        app.run(host='0.0.0.0', port=5000, debug=True)
    except Exception as e:
        print(f"Failed to start the server: {str(e)}")