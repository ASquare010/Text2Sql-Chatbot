from flask import Flask, request,render_template, jsonify
from utils.utils import pipelineAudio, fetch_property_details, textSqlApi 
from flask_cors import CORS
import base64

app = Flask(__name__)
CORS(app)  

@app.route('/')
def index(): 
    return render_template('index.html')

@app.route('/upload_audio', methods=['POST'])
def upload_audio():

    audio_buffer, message, transcribe, ids = pipelineAudio(request.files['audio_data'])
      
    message = message.replace('\n', '<br>')
    fetch_property = fetch_property_details(ids)
    audio_base64 = base64.b64encode(audio_buffer.getvalue()).decode('utf-8')
       
    return jsonify({
        "message": message,
        "transcribed": transcribe,
        "audio": audio_base64,
        "property": fetch_property
    })

@app.route('/upload_text', methods=['POST'])
def upload_text():
    
    data = request.get_json()
    print('input->',data['text'])
    
    message, _ ,ids = textSqlApi(data['text'])
    message = message.replace('\n', '<br>')
    
    fetch_property = fetch_property_details(ids)
    
    print("fetch_property->",fetch_property)
    
    return jsonify({"message": message,"property":fetch_property})


if __name__ == '__main__': 
    app.run(host='127.0.0.1', debug=False)