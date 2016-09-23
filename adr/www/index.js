// var React = require('react');
// var ReactDOM = require('react-dom');
// var Plotly = require('plotly.js');
var Redux = require('redux');
var ReactRedux = require('react-redux');

var ws; //websocket
/**************
ACTIONS/data to update:
temps
instrument status:
    Compressor
    ruox
    diode
    power supply
    magnet Voltage
    heat Switch
    pump chart
log
regulating
magging up
pump cart pressure

T O D O :
make pressure component
make log component
write actions to send back commands to server
get real data from server
make different levels for plot times (1hr, 6hrs, 24hrs, etc)
put in temp to regulate at part/make it change when user changes it
make buttons unclickable when grey
**************/

/********** ACTIONS ***********/
const UPDATE_TEMPS = Symbol('UPDATE_TEMPS');
const updateTemps = (newState={}) => ({
    type: UPDATE_TEMPS,
    newState
});
const UPDATE_INSTRUMENTS = Symbol('UPDATE_INSTRUMENTS');
const updateInstruments = (newState={}) => ({
    type: UPDATE_INSTRUMENTS,
    newState
});
const UPDATE_LOG = Symbol('UPDATE_LOG');
const updateLog = (newState={datetime:'',message:''}) => ({
    type: UPDATE_LOG,
    newState
});
const UPDATE_STATE = Symbol('UPDATE_STATE');
const updateState = (newState={isMaggingUp:true,isRegulating:true, compressorOn:false, pressure:NaN}) => ({
    type: UPDATE_STATE,
    newState
});

/********* STATE REDUCER / STORE ************/
const stateReducer = (state={
    temps: {
        timeStamps:[],
        t60K:[],
        t03K:[],
        tGGG:[],
        tFAA:[]
    },
    instruments: {
        'Compressor': {server: false, connected: false},
        'Ruox Temperature Monitor': {server: false, connected: false},
        'Diode Temperature Monitor': {server: false, connected: false},
        'Power Supply': {server: false, connected: false},
        'Magnet Voltage Monitor': {server: false, connected: false},
        'Heat Switch': {server: false, connected: false},
        'Pump Cart Pressure': {server: false, connected: false}
    },
    log:[],
    isMaggingUp:true,
    isRegulating:true,
    compressorOn:false,
    pressure:1000
}, action) => {
    switch (action.type) {
        case UPDATE_LOG:
        return Object.assign( {}, state, {log: [state.log, action.newState]})
        case UPDATE_STATE:
        return Object.assign({},state,action.newState);
        case UPDATE_TEMPS:
        return Object.assign( {}, state, {temps: {
            timeStamps:[...state.temps.timeStamps, ...action.newState.timeStamps.map(Date)],
            t60K:[...state.temps.t60K, ...action.newState.t60K],
            t03K:[...state.temps.t03K, ...action.newState.t03K],
            tGGG:[...state.temps.tGGG, ...action.newState.tGGG],
            tFAA:[...state.temps.tFAA, ...action.newState.tFAA]
        }})
        case UPDATE_INSTRUMENTS:
        return Object.assign( {}, state, {instruments: Object.assign({},state.instruments,action.newState)})
        default:
        return state;
    }
};

const { createStore } = Redux;
const { Provider, connect } = ReactRedux;
const store = createStore(stateReducer);
const { getState, dispatch } = store;
const { createClass, PropTypes } = React;

/***** TEST STORE *********
console.log(getState());
dispatch(updateLog({dt:67,message:'hello'}));
console.log(getState());
dispatch(updateTemps({
    timeStamps: [1,2],
    t60K: [3,4],
    t03K: [5,6],
    tGGG: [7,8],
    tFAA: [9,0]
}));
dispatch(updateTemps({
    timeStamps: [1,2],
    t60K: [3,4],
    t03K: [5,6],
    tGGG: [7,8],
    tFAA: [9,0]
}));
console.log(getState());
**********************/

/********** COMPONENTS ***********/
const Temp = (props) => {
    var arrow = '\u21E7 ';
    if(props.rate < 0) { arrow = '\u21E9 '; }
    var rate = props.rate;
    if(isNaN(rate)) {
        arrow = ' ';
        rate = 'NaN'
    }
    else { rate = Math.abs(rate).toFixed(3); }
    // no idea why this is needed.  toPrecision was throwing error, but then
    // still working, so ???
    try {
        var temp = props.temp.toPrecision(4);
    } catch(err) {
        //console.log([props.label,props.temp])
        var temp = props.temp;
    }
    return(
        <div style={{border:'3px solid '+props.color}}>
          <div style={{color:'white', backgroundColor:props.color, display: 'inline-block', width:'33.333%'}}>{props.label}</div>
          <div style={{color:props.color, display: 'inline-block', width:'33.333%'}}>{temp}K</div>
          <div style={{color:props.color, display: 'inline-block', width:'33.333%', fontSize:18}}>
            <span style={{verticalAlign:'bottom'}}>[{arrow+rate}K/sec]</span>
          </div>
        </div>
    )
};
const mapStateToTempProps = (storeState,props) => {
    return {
        temps: storeState.temps
    }
}
const AllTemps = ({temps}) => {
    var end = temps.tFAA.length-1;
    var rate = (tempList) => (tempList[tempList.length-1] - tempList[tempList.length-2])
                            / (temps.timeStamps[tempList.length-1] - temps.timeStamps[tempList.length-2])*1000;
    return(
        <div>
            <Temp label="60K" color="#d62728" temp={temps.t60K[end]} rate={rate(temps.t60K)} />
            <Temp label="03K" color="#2ca02c" temp={temps.t03K[end]} rate={rate(temps.t03K)} />
            <Temp label="GGG" color="#ff7f0e" temp={temps.tGGG[end]} rate={rate(temps.tGGG)} />
            <Temp label="FAA" color="#1f77b4" temp={temps.tFAA[end]} rate={rate(temps.tFAA)} />
        </div>
    )
};
const TempDisplay = connect(mapStateToTempProps)(AllTemps);

const Instrument = (props) => {
    return(
        <div><span style={{color:props.color}}>{'\u25C9 '}</span>{props.label}</div>
    )
};
const mapStateToInstrumentProps = (storeState,props) => {
    return {
        instruments: storeState.instruments
    }
}
const AllInstruments = ({instruments}) => {
    var instrumentStatuses = Object.keys(instruments).map( function(instrName) {
        var statusColor = "#d62728"; //red
        if( instruments[instrName].server==true && instruments[instrName].connected==false ) { statusColor="#ff7f0e"; } //orange
        else if( instruments[instrName].server==true && instruments[instrName].connected==true ) { statusColor="#2ca02c"; } //green
        return <Instrument label={instrName} color={statusColor} />
    });
    return(<div>{instrumentStatuses}</div>)
};
const InstrumentDisplay = connect(mapStateToInstrumentProps)(AllInstruments);

const mapStateToOpenHSProps = (storeState,props) => {
    return {
        instruments: storeState.instruments
    }
}
const mapStateToCloseHSProps = (storeState,props) => {
    return {
        instruments: storeState.instruments
    }
}
const mapStateToMagUpProps = (storeState,props) => {
    return {
        isMaggingUp: storeState.isMaggingUp,
        isRegulating: storeState.isRegulating
    }
}
const mapStateToRegulateProps = (storeState,props) => {
    return {
        isMaggingUp: storeState.isMaggingUp,
        isRegulating: storeState.isRegulating
    }
}
const mapStateToCompressorProps = (storeState,props) => {
    return {
        instruments: storeState.instruments,
        compressorOn: storeState.compressorOn
    }
}

const OpenHSButton = connect(mapStateToOpenHSProps)( ({instruments}) => {
    if (instruments['Heat Switch'].server == true) {
        var buttonStyle = {width:'45%'};
        var buttonClick = (e) => ws.send(JSON.stringify({command:'Open Heat Switch'}));
    } else {
        var buttonStyle = {width:'45%', color: 'grey'};
        var buttonClick = (e) => (null);
    }
    return(
        <div className='button' style={buttonStyle} onClick={(e) => buttonClick(e)}> Open Heat Switch </div>
    )
});
const CloseHSButton = connect(mapStateToCloseHSProps)( ({instruments}) => {
    if (instruments['Heat Switch'].server == true) {
        var buttonStyle = {width:'45%'};
        var buttonClick = (e) => ws.send(JSON.stringify({command:'Close Heat Switch'}));
    } else {
        var buttonStyle = {width:'45%', color: 'grey'};
        var buttonClick = (e) => (null);
    }
    return(
        <div className='button' style={buttonStyle} onClick={(e) => buttonClick(e)}> Close Heat Switch </div>
    )
});
const MagUpButton = connect(mapStateToMagUpProps)( ({isMaggingUp,isRegulating}) => {
    if (isMaggingUp) {
        var buttonStyle = {};
        var text = 'Stop Magging Up';
        var buttonClick = (e) => ws.send(JSON.stringify({command:'Stop Magging Up'}));
    }
    else if (isRegulating) {
        var buttonStyle = {color: 'grey'};
        var text = 'Mag Up';
        var buttonClick = (e) => (null);
    }
    else {
        var buttonStyle = {};
        var text = 'Mag Up';
        var buttonClick = (e) => ws.send(JSON.stringify({command:'Mag Up'}));
    }
    return(
        <div className='button' style={buttonStyle} onClick={(e) => buttonClick(e)}> {text} </div>
    )
});
const RegulateButton = connect(mapStateToRegulateProps)( ({isMaggingUp,isRegulating}) => {
    if (isRegulating) {
        var buttonStyle = {};
        var text = 'Stop Regulating';
        var buttonClick = (e) => ws.send(JSON.stringify({command:'Stop Regulating'}));
    }
    else if (isMaggingUp) {
        var buttonStyle = {color: 'grey'};
        var text = 'Regulate';
        var buttonClick = (e) => (null);
    }
    else {
        var buttonStyle = {};
        var text = 'Regulate';
        var buttonClick = (e) => ws.send(JSON.stringify({command:'Regulate',temp:0}));
    }
    return(
        <div className='button' style={buttonStyle} onClick={(e) => buttonClick(e)}> {text} </div>
    )
});
const CompressorButton = connect(mapStateToCompressorProps)( ({instruments,compressorOn}) => {
    if (instruments['Compressor'].connected) {
        var buttonStyle = {};
        var text = compressorOn ? 'Stop Compressor' : 'Start Compressor'
        var buttonClick = (e) => ws.send(JSON.stringify({command:'Set Compressor State',on:false}));
    }
    else {
        var buttonStyle = {color: 'grey'};
        var text = 'Start/Stop Compressor';
        var buttonClick = (e) => (null);
    }
    return(
        <div className='button' style={buttonStyle} onClick={(e) => buttonClick(e)}> {text} </div>
    )
});
const RefreshInstrumentsButton = () => {
    var buttonClick = (e) => ws.send(JSON.stringify({command:'Refresh Instruments'}));
    return(
        <div className='button' onClick={(e) => buttonClick(e)}> Refresh Instruments </div>
    )
};


ReactDOM.render(<Provider store={ store }>
                    <div>
                        <OpenHSButton /><CloseHSButton />
                        <MagUpButton />
                        <RegulateButton />
                        <CompressorButton />
                        <RefreshInstrumentsButton />
                    </div>
                </Provider>,
                document.getElementById("buttonHolder"));
ReactDOM.render(<Provider store={ store }><TempDisplay /></Provider>,
    document.getElementById("tempDisplay"));
ReactDOM.render(<Provider store={ store }><InstrumentDisplay /></Provider>,
    document.getElementById("instrumentStatusDisplay"));


var d3 = Plotly.d3;

window.onload = function(){
    ws = new WebSocket("ws://localhost:9876/ws");
    //var s = new WebSocket("ws://localhost:1025/");
    ws.onopen = function(e) { console.log("socket opened"); }
    ws.onclose = function(e) { console.log("socket closed"); }
    ws.onmessage = function(e) {
        const newState = JSON.parse(e.data);
        console.log(newState);
        if (newState.hasOwnProperty('temps')) {
            dispatch(updateTemps(newState.temps));
            delete newState.temps;
        }
        if (newState.hasOwnProperty('instruments')) {
            dispatch(updateInstruments(newState.instruments));
            delete newState.instruments
        }
        if (newState.hasOwnProperty('log')) {
            dispatch(updateLog(newState.log));
            delete newState.log;
        }
        dispatch(updateState(newState));
    }

    var plotSpace = d3.select('#tempPlot').node();
    const { getState } = store;
    const { temps } = getState();
    const {timeStamps, t60K, t03K, tGGG, tFAA} = temps;
    var data = [
        {
          type: 'scatter',                    // set the chart type
          mode: 'lines',                      // connect points with lines
          name: 'FAA',
          x: timeStamps,                            // set the x-data
          y: tFAA,                        // set the x-data
          line: {                             // set the width of the line.
            width: 1
          }
        },{
          type: 'scatter',                    // set the chart type
          mode: 'lines',                      // connect points with lines
          name: 'GGG',
          x: timeStamps,                            // set the x-data
          y: tGGG,                        // set the x-data
          line: {                             // set the width of the line.
            width: 1
          }
        },{
          type: 'scatter',                    // set the chart type
          mode: 'lines',                      // connect points with lines
          name: '3K',
          x: timeStamps,                            // set the x-data
          y: t03K,                        // set the x-data
          line: {                             // set the width of the line.
            width: 1
          }
        },{
          type: 'scatter',                    // set the chart type
          mode: 'lines',                      // connect points with lines
          name: '60K',
          x: timeStamps,                            // set the x-data
          y: t60K,                        // set the x-data
          line: {                             // set the width of the line.
            width: 1
          }
        }
        ]
    Plotly.plot( plotSpace, data,
  {
      yaxis: {title: "Temperature [K]"},       // set the y axis title
      xaxis: {
        showgrid: false,                  // remove the x-axis grid lines
      },
      margin: {                           // update the left, bottom, right, top margin
        l: 50, b: 50, r: 10, t: 20
      }
  })

  store.subscribe( () => {
      const { getState } = store;
      const { temps } = getState();
      const {timeStamps, t60K, t03K, tGGG, tFAA} = temps;
      //plotSpace.data[0].x.push(d);
      plotSpace.data[0].x = timeStamps;
      plotSpace.data[0].y = tFAA;
      plotSpace.data[1].x = timeStamps;
      plotSpace.data[1].y = tGGG;
      plotSpace.data[2].x = timeStamps;
      plotSpace.data[2].y = t03K;
      plotSpace.data[3].x = timeStamps;
      plotSpace.data[3].y = t60K;
      Plotly.redraw(plotSpace);
  });

  var addRandomTempData = function() {
      dispatch(updateTemps({
          timeStamps:[new Date()],
          t60K: [20+Math.random()],
          t03K: [15+Math.random()],
          tGGG: [10+Math.random()],
          tFAA: [5+Math.random()]
      }));
      setTimeout(addTempData,1000);
  }
  //addRandomTempData()
}
window.onresize = function() {
    var plotSpace = d3.select('#tempPlot').node();
    Plotly.Plots.resize(plotSpace);
};