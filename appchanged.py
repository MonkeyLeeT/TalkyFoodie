from flask import Flask, render_template, session
from random import randint
from flask.ext.socketio import join_room, leave_room
from flask.ext.socketio import SocketIO, emit
import names, random
import numpy as np
import time
import numpy
import threading

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)
roomCurrTime = {}
users = []
fdict = {}
words = open("words.txt").read().splitlines()
foods = open("foodlist.txt").read().splitlines()
fakeusers = []
for i in range(10):
    fakeusers.append(names.get_first_name())

def readSentimentList(file_name):
    ifile = open(file_name, 'r')
    happy_log_probs = {}
    sad_log_probs = {}
    ifile.readline() #Ignore title row
    
    for line in ifile:
        tokens = line[:-1].split(',')
        happy_log_probs[tokens[0]] = float(tokens[1])
        sad_log_probs[tokens[0]] = float(tokens[2])

    return happy_log_probs, sad_log_probs

def classifySentiment(words, happy_log_probs, sad_log_probs):
    # Get the log-probability of each word under each sentiment
    happy_probs = [happy_log_probs[word] for word in words if word in happy_log_probs]
    sad_probs = [sad_log_probs[word] for word in words if word in sad_log_probs]

    # Sum all the log-probabilities for each sentiment to get a log-probability for the whole tweet
    tweet_happy_log_prob = np.sum(happy_probs)
    tweet_sad_log_prob = np.sum(sad_probs)

    # Calculate the probability of the tweet belonging to each sentiment
    prob_happy = np.reciprocal(np.exp(tweet_sad_log_prob - tweet_happy_log_prob) + 1)
    prob_sad = 1 - prob_happy

    return prob_happy, prob_sad

def Average(lis):
    r=0.0
    for i in lis:
        r+=i
    result=r/len(lis)
    return (round(result,5))
def list_all_dict(dict_a):#使用isinstance检测数据类型
    for x in range(len(dict_a)-1):
        temp_key = list(dict_a.keys())[x]
        temp_value = dict_a[temp_key]
        for y in range(len(temp_value)-1):
            key = list(temp_value.keys())[y]
            value = temp_value[key]
            scorefile = open('scorefile.txt','w').writelines(str(temp_key)+','+str(key)+','+str(value))
    global t
    t = threading.Timer(10.0, list_all_dict, [fdict])  
    t.start() 

def analyze(sentence, dic):
    happy_log_probs, sad_log_probs = readSentimentList('twitter_sentiment_list.csv')
    user_name = sentence.setdefault('user')
    lines = sentence.setdefault('message').split()
    hashtagfood = sentence.setdefault('food')
    dic.setdefault(user_name,{})
    tweet_happy_prob, tweet_sad_prob = classifySentiment(lines, happy_log_probs, sad_log_probs)
    if tweet_happy_prob > tweet_sad_prob:
        for word in lines:
            if word in foods:
                if word == hashtagfood:
                    dic[user_name].setdefault(word,[]).append(tweet_happy_prob)
                else: 
                    for keys in dic:
                        if keys!=user_name:
                            dic[keys].setdefault(word,[]).append(tweet_happy_prob+0.5)
                        elif  keys == user_name:
                            dic[keys].setdefault(word,[]).append(tweet_happy_prob)
    for x in range(len(dic)-1):
        k = list(dic.keys())[x]
        v = dic[k]
        for y in range(len(v)-1):
            key0 = list(v.keys())[y]
            value0 = list(v[key0]) #TypeError: 'numpy.float64' object is not iterable
            print (value0)
            dic[k][key0] = Average(value0) 
    return dic

@app.errorhandler(404)
def page_not_found():
    return "Sorry, this page was not found.", 404


@app.route("/")
def home():
    if 'username' not in session:
        while True:
            session['username'] = names.get_first_name()
            if session['username'] not in users:
                users.append(session['username'])
                break
    print (session['username'])
    return render_template("index.html", myUserName=session['username'])


@socketio.on('request host', namespace='/test')
def test_message(message):
    room = str(randint(1, 1000))
    emit('host confirm', {'data': room})
    join_room(room)


@socketio.on('request join', namespace='/test')
def test_message(message):
    room = message['data']
    join_room(room)
    emit('join confirm', {'data': room})


@socketio.on('chat broadcast', namespace='/test')
def room_chat(message):
    print (message)
    room = message['room']
    data = message['data']
    emit('chat message receive', {'data': data}, room=room)


@socketio.on('voice chat', namespace='/test')
def voice_chat(message):
    emit('voice message receive', {'data': message['data'], 'username': message['username']}, room=message['room'],
              broadcast=True, include_self=False)


@socketio.on('connect', namespace='/test')
def test_connect():
    emit('my response', {'data': 'Connected'})


@socketio.on('leave', namespace='/test')
def on_leave(message):
    room = message['room']
    leave_room(room)
    users.remove(message['username'])
    emit('chat message receive', message['username'] + ' has left the room.', room=room)
    print('leave')


@socketio.on('message', namespace='/test')
def spam(message):
    random_user = random.choice(fakeusers)
    random_food = random.choice(foods)
    random_sentence = {'user': random_user, 'food': random_food, 'message': (' '.join(random.sample(words, 10))).join(random.sample(foods, 2))}
    #work on this function!
    print(random_sentence['message'])
    fdict.update(analyze(random_sentence, fdict))
    t = threading.Timer(10.0, list_all_dict, [fdict])  
    t.start()


if __name__ == "__main__":
    socketio.run(app, '0.0.0.0', 8080)