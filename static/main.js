// Alert box functions
var windowPopUp = new Object();
windowPopUp.open = function(id, classes, titleText, bodyText, functionClose, textoClose){
    var close = (textoClose !== undefined)? textoClose: 'Close';
    var popBackground = '<div id="popBackground_' + id + '" class="popUpBackground ' + 'red' + '"></div>'
    var window = '<div id="' + id + '" class="popUp ' + classes + '"><h1>' + titleText + "</h1><div><span>" + bodyText + "</span></div><button class='puClose " + "alert" + "' id='" + id +"_Close' data-parent=" + id + ">" + close + "</button></div>";
    $("window, body").css('overflow', 'hidden');
    
    $("body").append(popBackground);
    $("body").append(window);
    $("body").append(popBackground);
     //alert(window);
    $("#popBackground_" + id).fadeIn("fast");
    $("#" + id).addClass("popUpInput");
    
    $("#" + id + '_Close').on("click", function(){
        if((functionClose !== undefined) && (functionClose !== '')){
            functionClose();
            
        }else{
            windowPopUp.close(id);
        }
    });
    
};
windowPopUp.close = function(id){
    if(id !== undefined){
        $("#" + id).removeClass("popUpInput").addClass("popUpOutput"); 
        
            $("#popBackground_" + id).fadeOut(1000, function(){
                $("#popBackground_" + id).remove();
                $("#" + $(this).attr("id") + ", #" + id).remove();
                if (!($(".popUp")[0])){
                    $("window, body").css('overflow', 'auto');
                }
            });
            
      
    }
    else{
        $(".popUp").removeClass("popUpInput").addClass("popUpOutput"); 
        
            $(".popUpBackground").fadeOut(1000, function(){
                $(".popUpBackground").remove();
                $(".popUp").remove();
                $("window, body").css('overflow', 'auto');
            });
            
       
    }
}




//Graph declarations
const ctx1 = document.getElementById('chart1').getContext('2d');
const ctx2 = document.getElementById('chart2').getContext('2d');
const ctx3 = document.getElementById('chart3').getContext('2d');
const ctx4 = document.getElementById('chart4').getContext('2d');

var graphData1 = {
    type: 'line',
    data: {
        datasets: [{
            label: 'Traffic Volume',
            data: [],
            backgroundColor: [
                'rgba(73, 198, 230, 0.5)',
            ],
            borderWidth: 1
        }]
    },
    options: {
        scales: {
            x : {
                type: 'time',
                time: {
                    displayFormats: {
                        millisecond: 'HH:mm:ss.SSS'
                    },
                    unit: 'millisecond'
                },
                ticks : {source: 'data'},
                grid: {display: false},
                title: {
                    display: true,
                    text: 'Time (milliseconds)'
                }
            },
            y: {
                grid: {display: false},
                title: {
                    display: true,
                    text: 'Traffic Volume (bytes)'
                }
            }
        }
    }
}
var graphData2 = {
    type: 'line',
    data: {
        datasets: [{
            label: '# of Unique Users',
            data: [],
            backgroundColor: '#7DF1AB',
            borderWidth: 1
        }]
    },
    options: {
        scales: {
            x : {
                type: 'time',
                time: {
                    displayFormats: {
                        millisecond: 'HH:mm:ss.SSS'
                    },
                    unit: 'millisecond'
                },
                ticks : {source: 'data'},
                grid: {display: false},
                title: {
                    display: true,
                    text: 'Time (milliseconds)'
                }
            },
            y: {
                grid: {display: false},
                title: {
                    display: true,
                    text: 'Unique Users (count)'
                }
            }
        }
    }
}
var graphData3 = {
    type: 'line',
    data: {
        datasets: [{
            label: 'Anomaly Probability',
            data: [],
            backgroundColor: '#D2A8E4',
            borderWidth: 1
        },
        {
            label: 'Anomaly Score',
            data: [],
            backgroundColor: '#4D4351',
            borderWidth: 1
        }]
    },
    options: {
        parsing: false,
        scales: {
            x : {
                type: 'linear',
                grid: {display: false},
                title: {
                    display: true,
                    text: 'Data Points'
                }
            },
            y: {
                beginAtZero: true,
                grid: {display: false}
            }
        }
    }
}
var graphData4 = {
    type: 'bar',
    data: {
        datasets: [{
            label: '# of Users',
            data: [],
            backgroundColor: '#FFBC93',
            borderWidth: 1
        }]
    },
    options: {
        scales: {
            x : {
                type: 'category',
                labels: [],
                grid: {display: false},
                title: {
                    display: true,
                    text: 'Destination Port'
                }
            },
            y: {
                beginAtZero: true,
                grid: {display: false}
            }
        }
    }
}

const graphDatas = [graphData1, graphData2, graphData3, graphData4];
const charts = [new Chart(ctx1, graphData1), new Chart(ctx2, graphData2), new Chart(ctx3, graphData3), new Chart(ctx4, graphData4)];

//Data receiver
function connect(){
    var socket =  new WebSocket('ws://localhost:8000/ws/graph/');

    socket.onopen = function(e) {
        console.log("Websocket connection established")
    }

    socket.onmessage = function(e){
        var serverData = JSON.parse(e.data);
        console.log(serverData);

        var serverDataKeys = Object.keys(serverData)
        
        for(let i = 0; i < 4; i++){
            var newGraphData = graphDatas[i].data.datasets[0].data
            if (newGraphData.length > 10){
                newGraphData.shift()
            }
            if (i == 0 && serverDataKeys.includes('traffic_vol')){
                newGraphData.push({
                    x: serverData.traffic_vol[0].received_time,
                    y: serverData.traffic_vol[0].total_payload});
                
                graphDatas[i].data.datasets[0].data = newGraphData
                charts[i].update()
            }
            else if(i == 1 && serverDataKeys.includes('users')){
                newGraphData.push({
                    x: serverData.users[0].received_time,
                    y: serverData.users[0].users});
                
                graphDatas[i].data.datasets[0].data = newGraphData
                charts[i].update()
            }
            else if(i == 2 && serverDataKeys.includes('anomaly_plot')){
                var inputs = []
                var anomalies = []
                var anomalyProb = []
            
                serverData.anomaly_plot.time.map(
                    (val, ind) =>{
                        inputs.push({x: val, y: serverData.anomaly_plot.data[ind]})
                        anomalies.push({x: val, y: serverData.anomaly_plot.anomalies[ind]})
                        anomalyProb.push({x: val, y: serverData.anomaly_plot.anomaly_prob[ind]})
                    }
                )
                if(inputs.length > 500){
                    inputs.splice(0,inputs.length-500)
                    anomalies.splice(0,anomalies.length-500)
                    anomalyProb.splice(0,anomalyProb.length-500)
                }
                graphDatas[2].data.datasets[0].data = anomalyProb
                graphDatas[2].data.datasets[1].data = anomalies
                charts[2].update()
            }
            else if(i == 3){
                graphDatas[i].data.datasets[0].data = serverData.port.users
                graphDatas[i].options.scales.x.labels = serverData.port.dport
                
                charts[i].update()
            }
    
        }
            
            

        if (serverData.anomaly_detected == true){
            var myText = "Traffic Anomaly Detected";
            windowPopUp.open( "alert1", "p red", "ALERT", myText)
        }
    }

    socket.onclose = function(event){
        console.log("Connection closed with code: "+event.code)
        if(event.code != 1000){
            console.log("Attempting to reconnect as connection is dropped unexpectedly in 3s")
            setTimeout(function() {
                console.log("Reconnecting...");
                connect();
            }, 3000);
        };
        
    };

    socket.onerror = function(err){
        console.log("Websocket encountered error: " + err.message)
    }
}
connect();