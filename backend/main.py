import os
import urllib.request
#from app import app
from flask import Flask, request, redirect, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from flask_cors import CORS, cross_origin

#for GCP cloud storage
from google.cloud import storage


#for GCP cloud SQL
import sqlalchemy


#for list flatten
from pandas.core.common import flatten

#from flask import Flask
#from flask_cors import CORS, cross_origin

UPLOAD_FOLDER = './uploads'

app = Flask(__name__)
cors = CORS(app)

app.config['CORS_HEADERS'] = 'Content-Type'
app.secret_key = "secret key"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

db_user = "master_capsum"
#db_user = "root"
db_password = "aiccsql@2020"
db_name = "capsum_db"
db_connection_name = "capsum-project-292904:us-central1:capsum-sql"

#import sys
#sys.path.insert(1, './caption/')
#from caption.gen_cap import GenCap

def insert_query_execute(db,query):
    stmt = sqlalchemy.text(query)

    with db.connect() as conn:
        conn.execute(stmt)


def select_query_execute(db,query):

    stmt = sqlalchemy.text(query)

    with db.connect() as conn:
        rs = conn.execute(stmt)

        result = []
		
        for row in rs:
        	result.append(list(row))

    return result


import sys

ALLOWED_EXTENSIONS = set(['mp4'])

def allowed_file(filename):
	return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET'])
@cross_origin()
def index():
    return 'Hello'

@app.route('/login', methods=['POST'])
@cross_origin()
def login():
	if 'user' not in request.get_json():
		resp = jsonify({'message' : 'user not provided'})
		resp.status_code = 400
		return resp
	else:
		print(request.get_json()['user'])
	
		########//send this to Db remaining tput variable get in json
		db = sqlalchemy.create_engine('mysql+pymysql://master_capsum:aiccsql@2020@127.0.0.1:3306/capsum_db')
		#db = sqlalchemy.create_engine('mysql+pymysql://master_capsum:aiccsql@2020@/capsum_db?unix_socket=/cloudsql/capsum-project-292904:us-central1:capsum-sql')
		uemail = request.get_json(force=True)['user']['email']
		uname = request.get_json(force=True)['user']['fname'] +' '+request.get_json()['user']['lname']
		query1 = "select user_email from user;"
		query2 = "insert into user(user_email,user_name) values ('"+uemail+"','"+uname+"');"
		result = select_query_execute(db,query1)
		result=list(flatten(result))
		
		if not uemail in result:
			insert_query_execute(db,query2)

		return jsonify({'message' : 'OK Logged in'})

@app.route('/getvid', methods=['POST'])
@cross_origin()
def getVids():
	
	
	if 'email' not in request.headers:
		resp = jsonify({'message' : 'No file part in the request'})
		resp.status_code = 400
		return resp
	else:
		#print(request.get_json()['user'])
		########//get vids from gcp storage
		uemail = request.headers.get('email')
		db = sqlalchemy.create_engine('mysql+pymysql://master_capsum:aiccsql@2020@127.0.0.1:3306/capsum_db')
		#db = sqlalchemy.create_engine('mysql+pymysql://master_capsum:aiccsql@2020@/capsum_db?unix_socket=/cloudsql/capsum-project-292904:us-central1:capsum-sql')
		'''
		resp = []
		for file in os.listdir('./vids/'):
			if os.path.isfile('./vids/'+file):
				if(file.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS):
						#upload_file
					thumbnail=file.rsplit('.', 1)[0]+'.png'
					d = {'vid':file, 'thumb':thumbnail}
					print(d)
					resp.append(d)
		'''
		'''
		{
			title:'songs1',
			thumbnail:["https://upload.wikimedia.org/wikipedia/commons/7/7c/Aspect_ratio_16_9_example.jpg","https://upload.wikimedia.org/wikipedia/commons/7/7c/Aspect_ratio_16_9_example.jpg","https://upload.wikimedia.org/wikipedia/commons/7/7c/Aspect_ratio_16_9_example.jpg"],
			urls:['https://www.youtube.com/watch?v=nY1g7hF7CyE','https://www.youtube.com/watch?v=hOC-lSVlF9s','https://www.youtube.com/watch?v=jwPmj0P8-H4'],
			captions:['a song is playing','something happening','just another video']
		},
		'''
		#title,thumbnail url,clip url,caption
		query1 = "select DISTINCT vid_name from video where user_id = (SELECT user_id FROM user WHERE user.user_email = '"+uemail+"');"
		result = select_query_execute(db,query1)
		vids=list(flatten(result))
		resp = []
		print(vids)
		for vid in vids:
			print(vid)
			q = "select clip_url, clip_thumbnail_url, caption from video where user_id=(SELECT user_id FROM user WHERE user.user_email = '"+uemail+"') and vid_name='"+str(vid)+"';"
			print(q)
			result = select_query_execute(db,q)
			print(result)
			clip_url, clip_thumbnail_url, caption =[],[],[]
			for r in result:
				clip_url.append(r[0])
				clip_thumbnail_url.append(r[1])
				caption.append(r[2])


			d = {'title':vid,'thumbnail':clip_thumbnail_url,'urls':clip_url,'captions':caption}
			 		
			resp.append(d)

		print(resp)
		resp = jsonify({'resp' : resp})
		return resp



@app.route('/upload', methods=['POST'])
@cross_origin()
def upload_file():
	# check if the post request has the file part
	if 'file' not in request.files:
		resp = jsonify({'message' : 'No file part in the request'})
		resp.status_code = 400
		return resp
	file = request.files['file']
	if file.filename == '':
		resp = jsonify({'message' : 'No file selected for uploading'})
		resp.status_code = 400
		return resp
	if file and allowed_file(file.filename):
        #make a connection with GCP cloud storage
		storage_client =  storage.Client.from_service_account_json('capsum-project-292904-55b0f1f3ac4d.json')
		BUCKET_NAME = 'capsum_video_storage_bucket'
		bucket = storage_client.get_bucket(BUCKET_NAME)

		filename = secure_filename(file.filename)
		try:
			os.system('mkdir ./uploads')
		except:
			pass
		
		file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
		process_folder=filename.rsplit('.', 1)[0]
		try:
			os.system('mkdir ./process/')
			os.system('mkdir ./process/'+process_folder)
			os.system('mkdir ./process/'+process_folder+'/output')
		except:
			pass

		print("HEREEE")
		os.system('cp '+os.path.join(app.config['UPLOAD_FOLDER'], filename)+' ./process/')
		
		os.system('python3 ./summarizer/test.py ./process/'+filename)
		captions=[]
		
		from caption.gen_cap import GenCap
		files=os.listdir('./process/'+process_folder+'/output/')
		captions=GenCap('./process/'+process_folder+'/output/',files)
		#captions=GenCap('./uploads/',['summarized1.mp4'])
		#captions=['a woman is walking', 'a man is moving a gun', 'a man is walking', 'a man is driving a road', 'a man is pouring a water into a water','asdasd']
		print(captions)
		'''
		if not os.path.exists('process/'+process_folder+'/output/'+filename.rsplit('.', 1)[0]+'.png'):
			os.system('ffmpeg -i '+'process/'+process_folder+'/output/'+filename+' -ss 00:00:03 -vframes 1 ./process/'+process_folder+'/output/'+filename.rsplit('.', 1)[0]+'.png')
		'''

		uemail = request.headers.get('email')
		clip_url = []
		thumbnail_url = []
		##generate thumbnails
		for fname in files:

			#upload summarized clip to cloud storage and get url
			fnames = "%s/%s" % (uemail+'/'+filename.rsplit('.', 1)[0],fname)
			blob = bucket.blob(fnames)
			with open('./process/'+process_folder+'/output/'+fname,'rb') as f:
				blob.upload_from_file(f,timeout=120)
			c_url = blob.public_url
			clip_url.append(c_url)

			#generate thumbnail for clip
			if not os.path.exists('./process/'+process_folder+'/output/'+fname.rsplit('.', 1)[0]+'.png'):
				os.system('ffmpeg -i '+'./process/'+process_folder+'/output/'+fname+' -ss 00:00:00 -vframes 1 ./process/'+process_folder+'/output/'+fname.rsplit('.', 1)[0]+'.png')

			#upload thumbnail for clip to cloud storage and get url
			fnames = "%s/%s" % (uemail+'/'+filename.rsplit('.', 1)[0],fname.rsplit('.', 1)[0]+'.png')
			blob = bucket.blob(fnames)
			with open('./process/'+process_folder+'/output/'+fname.rsplit('.', 1)[0]+'.png','rb') as f:
				blob.upload_from_file(f,timeout=120)
			t_url = blob.public_url
			thumbnail_url.append(t_url)

					
		#########upload summarized video to gcp storage
        
		'''
		uemail = request.headers.get('email')
        for fname in files:
            fnames = "%s/%s" % (uemail+'/'+filename.rsplit('.', 1)[0],fname)
            blob = bucket.blob(fnames)
            with open('process/'+process_folder+'/output/'+fname,'rb') as f:
                blob.upload_from_file(f,timeout=120)
		'''
		########send captions to DB
		########send video data to DB
		db = sqlalchemy.create_engine('mysql+pymysql://master_capsum:aiccsql@2020@127.0.0.1:3306/capsum_db')
		#db = sqlalchemy.create_engine('mysql+pymysql://master_capsum:aiccsql@2020@/capsum_db?unix_socket=/cloudsql/capsum-project-292904:us-central1:capsum-sql')

		#get user id
		q =  "select user_id from user where user_email = '"+uemail+"';"
		result = select_query_execute(db,q)
		uid = result[0][0]

		query1 = "SELECT max(original_vid_id) FROM video WHERE user_id = "+str(uid)+";"
		result = select_query_execute(db,query1)
		
		if result[0][0] == None:
			original_vid_id = 1
		else:
			original_vid_id = result[0][0]+1

		print(len(clip_url))
		print(len(thumbnail_url))
		print(len(captions))

		for i in range(len(clip_url)):
			q = "insert into video(original_vid_id,user_id,clip_id,vid_name,clip_url,clip_thumbnail_url,caption) values("+str(original_vid_id)+","+str(uid)+","+str(i+1)+",'"+filename.rsplit('.', 1)[0]	+"','"+str(clip_url[i])+"','"+str(thumbnail_url[i])+"','"+str(captions[i])+"');"
			insert_query_execute(db,q)



		resp = jsonify({'message' : 'File successfully uploaded','captions':captions})
		resp.status_code = 201
		return resp
	else:
		resp = jsonify({'message' : 'Allowed file types are mp4'})
		resp.status_code = 400
		return resp

if __name__ == "__main__":
    app.run(host='0.0.0.0',port=8080,threaded=True)
