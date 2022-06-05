import numpy as np
import cv2
import time
from switch import TestThreading
import os
from watch import Watcher,TimeLimit
from camera_thread import VideoStreamWidget
from just import predict
from pinreq import pin
import requests
from asset import get_dict
import pymysql
from datetime import datetime

#from aws_rds import insert_details
from duration import duration

if eval(os.getenv('DEMOGRAPHICS')):
    from facelib import FaceDetector, AgeGenderEstimator
    face_detector = FaceDetector()
    age_gender_detector = AgeGenderEstimator()



w = Watcher(0)
t = TimeLimit()

rng=int(os.getenv('TEMP_RANGE'))
a_rng=int(os.getenv('AGE_RANGE'))
lat=os.getenv('LATITUDE')
lng=os.getenv('LONGITUDE')
key=os.getenv('KEY')
url=os.getenv('URL').format(lat,lng,key)
rds_host = os.getenv('DB_HOST')
rds_user = os.getenv('DB_USER')
rds_pass = os.getenv('DB_PASSWORD')
rds_db = os.getenv('DB_NAME')
device = os.getenv('DEVICE_ID')
device_type = os.getenv('DEVICE_TYPE')
site = int(os.getenv('SITE_ID'))




conn = pymysql.connect(host= rds_host,user = rds_user, password = rds_pass,database = rds_db)
cur=conn.cursor()

def insert_details(name,mimetype,count,gender_age):
    timestamp = datetime.now()
    cur.execute("INSERT INTO raw_data(site_id,device,name,mimetype,count,gender_age,timestamp) VALUES (%s,%s,%s,%s,%s,%s,%s)",(site,str(device),str(name),str(mimetype),count,str(gender_age),str(timestamp)))
    conn.commit()


def sendtoserver(frame):
    imencoded = cv2.imencode(".jpg", frame)[1]
    file = {'image': ('image.jpg', imencoded.tobytes(), 'image/jpeg', {'Expires': '0'})}
    s = time.time()
    response = requests.post(os.getenv('MODEL_URL'), files=file, timeout=5) #3.110.0.141:5000
    e = time.time()
    j = response.json()
    result = [i for i in j if i['confidence'] > 0.6 and i['class'] == 0]
    return result,round(e-s,2)





def temp(lat,lng,key,rng):
    day=time.strftime("%p")
    c =int(float(requests.get(url).json()['current']['temp'])-273.15)
    
    if 1 <= c <= rng:
        a = 'R1'
        
    elif 1+rng <= c <= 2 * rng:
        a = 'R2'
        
    else:
        a = 'R3'
    
    return day+a






if __name__ == "__main__":
    src = os.getenv('STREAM_SRC') #175.101.82.215:1024/Streaming/Channels/502
    print(src)
    print(eval(os.getenv('DEMOGRAPHICS')))
    
    video_stream_widget = VideoStreamWidget(src)
    time.sleep(1)
     
    while True:
        
        #count = predict(video_stream_widget.frame)
        try:
            result,it = sendtoserver(video_stream_widget.frame)
        except:
            print('Video stream not detected')
            time.sleep(10)
            continue
        count = len(result)
        #print(it)


        if count is None:
            time.sleep(10)
            continue

        watch = w.variable < count
        print(watch,w.variable,count,it)
        
                
        if count >= 1 and watch:

            
            if eval(os.getenv('DEMOGRAPHICS')):
                
                try:
                    faces, boxes, scores, landmarks = face_detector.detect_align(video_stream_widget.frame)
                    # pin('on',[21,26])
                    try:
                        genders, ages = age_gender_detector.detect(faces)
                        gender_age=(genders,ages)
                        print(gender_age)

                    except:
                        time.sleep(5)
                        print('genders ages not detected')
                        continue
                    z = tuple(zip(genders,ages))
                    g = genders.count('Male') > genders.count('Female')
                    ages_males = [ y for x, y in z if x  == 'Male' ]
                    m_classifications = [(i//a_rng + 1) for i in ages_males]
                    ages_females = [ y for x, y in z if x  == 'Female' ]
                    f_classifications = [(i//a_rng + 1) for i in ages_females]

                    
                    if g:
                        m = max(m_classifications,key=m_classifications.count)
                        r1=temp(lat,lng,key,rng)+'MC'+str(m)
                        
                    else:
                        f = max(f_classifications,key=f_classifications.count)
                        r1=temp(lat,lng,key,rng)+'FC'+str(f)

                except:
                    gender_age=None
                    r1=temp(lat,lng,key,rng)
                    video_stream_widget = VideoStreamWidget(src)


            else:
                gender_age=None
                r1 = temp(lat,lng,key,rng)

            print(r1)
            asset=os.getenv(r1)
            print(asset)
            data_dict = get_dict(asset)
            mimetype = data_dict[0]
            name = data_dict[-1]
            print(name)
            duration = int(data_dict[1])

            if t.check_value() > duration:
                print(asset)
                print('playing ad..',r1)
                TestThreading(asset)
                insert_details(name,mimetype,count,gender_age)
                time.sleep(duration+1)






        w.check_value(count)
        # video_stream_widget.show_frame()
        # key = cv2.waitKey(1)
        # if key & 0xFF == ord('q'):
        #     break
