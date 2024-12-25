from sqlalchemy import text
from pydub import AudioSegment
import random, io, re, os
import pandas as pd 
from utils.appState import AppState

appState = AppState()

def transcribe(audio_data) -> str:
    
    audio_blob_bytes = audio_data.read()
    audio = AudioSegment.from_file(io.BytesIO(audio_blob_bytes))
    audio = audio.set_frame_rate(22050)
    audio = audio.set_channels(1)
    audio = audio.set_sample_width(2)  

    wav_io = io.BytesIO()
    audio.export(wav_io, format="wav")
    wav_io.seek(0) 
    
    directory = 'temp'
    file_path = os.path.join(directory, f'{random.randint(1, 10000)}_audio.wav')

    if not os.path.exists(directory):
        os.makedirs(directory)

    with open(file_path, 'wb') as f:
        f.write(wav_io.read())
   
    try:
        with open(file_path, "rb") as audio_file:
            transcription = AppState().client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="en"
            )
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

    return transcription.text

def split_answer_summary(text: str) -> (str, str): # type: ignore
    answer_match = re.search(r'<response>(.*?)</response>', text, re.DOTALL)
    summary_match = re.search(r'<speak>(.*?)</speak>', text, re.DOTALL)

    answer = answer_match.group(1).strip() if answer_match else text
    summary = summary_match.group(1).strip() if summary_match else ""

    return answer, summary

def extract_property_ids(results:list) -> list:
    try:
        elem = []
        for item in results:
            if isinstance(item[0], (int)):
                elem.append(item[0])
        return elem
    except:
        return []
 
def fetch_property_details(property_ids: list):
    if not property_ids:
        return None

    try:
        placeholders = ','.join([':p{}'.format(i) for i in range(len(property_ids))])
        query = f"""
            SELECT PropertyID, LatestListingPrice, MLSListingAddress, BedroomsTotal, BathroomsFull, AvgMarketPricePerSqFt, ListingAgentFullName, PhotosCount, PhotoKey, PhotoURLPrefix
            FROM properties 
            WHERE PropertyID IN ({placeholders})
        """
        parameters = {'p{}'.format(i): id_ for i, id_ in enumerate(property_ids)}

        with AppState().db.connect() as connection:
            result = connection.execute(text(query), parameters)
            df = pd.DataFrame(result.fetchall(), columns=[
                'PropertyID', 'LatestListingPrice', 'MLSListingAddress', 
                'BedroomsTotal', 'BathroomsFull', 'AvgMarketPricePerSqFt', 'ListingAgentFullName', 'PhotosCount', 'PhotoKey', 'PhotoURLPrefix'
            ])
        return df.to_json(orient='records')

    except Exception as e:
        return None

def openai_api(user_query, agent_name, max_tokens=1024, streaming=False):

    AppState().agents[agent_name]["memory"].append({"role": "user", "content": user_query})
    mem = AppState().agents[agent_name]["memory"]

    try:

        response = AppState().client.chat.completions.create(
        model = AppState().MODEL_NAME,
        messages = mem,
        max_tokens = max_tokens, 
        stream=streaming)

        assistant = response.choices[0].message.content
        AppState().agents[agent_name]["memory"].append({"role": "assistant", "content": assistant}),
        return assistant

    except Exception as e:
        return f"Exception in openAiApi {e}"
       
def textSqlApi(user_query):
    
    ids = []
    results=''
    response=''
    summary=''
    isException = "The SQL query successfully retrieved results from the database."


    sql = openai_api(user_query = user_query, agent_name = AppState().SQL_Agent).strip().replace("`", "").replace("sql\n", "")

    try:
        if sql:
            results = AppState().run_query(query=sql)

        ids = extract_property_ids(results)
        
    except Exception as e:
        print("Exception in DB->",e) 
        isException = e
    
    prompt = AppState().make_estate_agent_prompt(user_query,results,sql,isException)
    response = openai_api(user_query = prompt, agent_name = AppState().ESTATE_Agent)

    print("\nsql->",sql,"LLm Output->",response)
    response,summary = split_answer_summary(response)

    if(summary != ""):
      response = "<b>"+summary+"</b><br><br>"+response
    
    return response, summary ,ids

def ttsApi(text):
    
    spoken_response = AppState().client.audio.speech.create(
        model=AppState().TTS,
        voice=AppState().SPEAKER_NAME,
        response_format="wav",
        input=text
    )

    buffer = io.BytesIO()
    for chunk in spoken_response.iter_bytes(chunk_size=4096):
        buffer.write(chunk)
    buffer.seek(0)

    return buffer 

def pipelineAudio(audio_data):
    
    transcribed = transcribe(audio_data)
    print("whisper->",transcribed)
    message , summary ,ids = textSqlApi(transcribed)
    audio_buffer = ttsApi(summary)

    return audio_buffer, message, transcribed, ids