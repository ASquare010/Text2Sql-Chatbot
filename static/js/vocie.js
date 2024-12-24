let isRecording = false;
let mediaRecorder;
let chunks = [];

const playAnim = document.getElementById('playAnim');
const idelAnim = document.getElementById('stopAnim');
const loadingAnim = document.getElementById('playLoading');
const chatbotMessages = document.getElementById('chatbot-messages');
const messageInput = document.getElementById('messageInput');

messageInput.addEventListener('keypress', function(event) {
  if (event.key === 'Enter') {
    event.preventDefault(); 
    sendText();
  }
});

function chatAnimState(state) {

  if (state == "playing") {
    playAnim.hidden = false;
    idelAnim.hidden = true;
    loadingAnim.hidden = true;
  }
  else if (state == "loading"){
    playAnim.hidden = true;
    idelAnim.hidden = true;
    loadingAnim.hidden = false;
  }
  else{
    playAnim.hidden = true;
    idelAnim.hidden = false;
    loadingAnim.hidden = true;
  }

}

function chatMessage(message, isUser) {
  let div = document.createElement('div'); 
  div.className = (isUser === true) ? 'message user-message' : 'message bot-message'; 
  div.innerHTML = `<p><span class='timestamp'>${new Date().toLocaleTimeString()}</span> ${message}</p>`; 
  chatbotMessages.appendChild(div);
  chatbotMessages.scrollTop = chatbotMessages.scrollHeight;
}


function chat(message,isUser,animState) {
  chatAnimState(animState);
  chatMessage(message,isUser); 
}


function updatePropertyCards(properties) {

  // Clear the existing cards if properties are available

  if (Array.isArray(properties) && properties.length !== 0) {
      const listCard = document.createElement('div');
      listCard.innerHTML = '';  
      listCard.classList.add("horizontal-list-view");

      // Append new cards
      properties.forEach(property => {
          const cardHtml = `
              <div class="card">
                  <img src="/static/assets/house.png" alt="Image" class="card-image">
                  <div class="card-info">
                      <div class="card-header">
                          <span class="card-featured" hidden="true">Featured</span>
                          <p class="card-price">$${property.LatestListingPrice}</p>
                      </div>
                      <p class="card-address">${property.MLSListingAddress}</p>
                      <div class="card-details">
                          <p>${property.BedroomsTotal} Beds</p>
                          <p>&bull; ${property.BathroomsFull} Baths</p>
                          <p>&bull; ${property.AvgMarketPricePerSqFt} SqFt</p>
                      </div>
                      <div class="card-agent">
                          <img src="/static/assets/marea.png" alt="Agent" class="agent-image">
                          <p class="agent-name">${property.ListingAgentFullName}</p>
                      </div>
                      <p class="listing-age" hidden="true">6 months ago</p>
                  </div>  
              </div>`;

          listCard.innerHTML += cardHtml; // Append new card
      });

      chatbotMessages.appendChild(listCard);
      chatbotMessages.scrollTop = chatbotMessages.scrollHeight;
  }
}


async function toggleRecording() {
  if (!isRecording) {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);
    
    mediaRecorder.ondataavailable = function(event) {
      chunks.push(event.data);
    }

    mediaRecorder.onstop = async function() {
      const audioBlob = new Blob(chunks, { 'type': 'audio/wav; codecs=opus' });

      const formData = new FormData();
      chatAnimState("loading");
      formData.append('audio_data', audioBlob, 'recorded_audio.wav');

      chunks = [];

      $.ajax({
        url: 'http://127.0.0.1:5000/upload_audio',
        type: 'POST',
        data: formData,
        processData: false,
        contentType: false,
        success: function(data) {
          chatMessage(data['transcribed'], true);
          chatMessage(data['message'], false);

          const properties = JSON.parse(data['property']);

          console.log("properties",properties)
          // Update the property cards
          updatePropertyCards(properties);
          
          const audioUrl = `data:audio/wav;base64,${data['audio']}`;
          playAudio(audioUrl);
        },
        error: function(error) {
          chat("Error", false, "idel");
        }
      });
    }

    mediaRecorder.start();
    document.getElementById('micBtn').style.backgroundColor = '#e9c4c4';
    document.getElementById('micBtn').title = 'Stop Recording';
  } else {
    mediaRecorder.stop();
    document.getElementById('micBtn').style.backgroundColor = 'white';
    document.getElementById('micBtn').title = 'Start Recording';
  }

  isRecording = !isRecording;
}

function sendText() {

  const messageInput = document.getElementById('messageInput');
  const message = messageInput.value; 
 
  chat(message,true,"loading"); 
  messageInput.value = '';

  $.ajax({
    url: 'http://127.0.0.1:5000/upload_text',
    type: 'POST',
    contentType: 'application/json',
    data: JSON.stringify({ text: message }),
    success: function(data) {
        messageInput.value = ''; 
        
        let properties = JSON.parse(data['property']);

        chat(data['message'],false,"idel"); 
        
        console.log(data)
        updatePropertyCards(properties);
    },
  
    error: function(error) {
      chat("Error",false,"idel");
    }
  });
}


function playAudio(audioUrl) {
  const audioPlayer = document.getElementById('audioPlayer');

  audioPlayer.src = audioUrl;
  audioPlayer.play();

  audioPlayer.onplay = function() {
    chatAnimState("playing");
  };

  audioPlayer.onended = function() {
    chatAnimState("idel");
  };

  audioPlayer.onpause = function() {
    chatAnimState("idel");
  };
}