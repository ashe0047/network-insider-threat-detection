from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

from htm.bindings.sdr import SDR, Metrics
from htm.encoders.rdse import RDSE, RDSE_Parameters
from htm.encoders.date import DateEncoder
from htm.bindings.algorithms import SpatialPooler
from htm.bindings.algorithms import TemporalMemory
from htm.algorithms.anomaly_likelihood import AnomalyLikelihood
from htm.bindings.algorithms import Predictor

class HTM:
    def __init__(self) -> None:
        self.default_parameters = {
            # there are 2 (3) encoders: "value" (RDSE) & "time" (DateTime weekend, timeOfDay)
            'enc': {
                "value" :
                    {'resolution': 0.88, 'size': 700, 'sparsity': 0.02},
                "time": 
                    {'timeOfDay': (30, 1), 'weekend': 21}
            },
            'predictor': {'sdrc_alpha': 0.1},
            'sp': {'boostStrength': 3.0,
                    'columnCount': 1638,
                    'localAreaDensity': 0.04395604395604396,
                    'potentialPct': 0.85,
                    'synPermActiveInc': 0.04,
                    'synPermConnected': 0.13999999999999999,
                    'synPermInactiveDec': 0.006},
            'tm': {'activationThreshold': 17,
                    'cellsPerColumn': 13,
                    'initialPerm': 0.21,
                    'maxSegmentsPerCell': 128,
                    'maxSynapsesPerSegment': 64,
                    'minThreshold': 10,
                    'newSynapseCount': 32,
                    'permanenceDec': 0.1,
                    'permanenceInc': 0.1},
            'anomaly': {'period': 1000},
            }
        # self.input = self.process_input(input)
        # self.input_len = len(self.input)
        self.anomaly_value = 0
        self.anomalies     = []
        self.anomalyProb = []
        self.predictions = {1: [], 5: []}
        self.inputs = []


        #HTM parameters
        self.parameters = self.default_parameters
        # Make the Encoders.  These will convert input data into binary representations.
        self.dateEncoder = DateEncoder(timeOfDay= self.parameters["enc"]["time"]["timeOfDay"], 
                                    weekend  = self.parameters["enc"]["time"]["weekend"]) 
        
        self.scalarEncoderParams            = RDSE_Parameters()
        self.scalarEncoderParams.size       = self.parameters["enc"]["value"]["size"]
        self.scalarEncoderParams.sparsity   = self.parameters["enc"]["value"]["sparsity"]
        self.scalarEncoderParams.resolution = self.parameters["enc"]["value"]["resolution"]
        self.scalarEncoder = RDSE( self.scalarEncoderParams )
        self.encodingWidth = (self.dateEncoder.size + self.scalarEncoder.size)
        self.enc_info = Metrics( [self.encodingWidth], 999999999 )

        # Make the HTM.  SpatialPooler & TemporalMemory & associated tools.
        self.spParams = self.parameters["sp"]
        self.sp = SpatialPooler(
            inputDimensions            = (self.encodingWidth,),
            columnDimensions           = (self.spParams["columnCount"],),
            potentialPct               = self.spParams["potentialPct"],
            potentialRadius            = self.encodingWidth,
            globalInhibition           = True,
            localAreaDensity           = self.spParams["localAreaDensity"],
            synPermInactiveDec         = self.spParams["synPermInactiveDec"],
            synPermActiveInc           = self.spParams["synPermActiveInc"],
            synPermConnected           = self.spParams["synPermConnected"],
            boostStrength              = self.spParams["boostStrength"],
            wrapAround                 = True
        )
        self.sp_info = Metrics( self.sp.getColumnDimensions(), 999999999 )

        self.tmParams = self.parameters["tm"]
        self.tm = TemporalMemory(
            columnDimensions          = (self.spParams["columnCount"],),
            cellsPerColumn            = self.tmParams["cellsPerColumn"],
            activationThreshold       = self.tmParams["activationThreshold"],
            initialPermanence         = self.tmParams["initialPerm"],
            connectedPermanence       = self.spParams["synPermConnected"],
            minThreshold              = self.tmParams["minThreshold"],
            maxNewSynapseCount        = self.tmParams["newSynapseCount"],
            permanenceIncrement       = self.tmParams["permanenceInc"],
            permanenceDecrement       = self.tmParams["permanenceDec"],
            predictedSegmentDecrement = 0.0,
            maxSegmentsPerCell        = self.tmParams["maxSegmentsPerCell"],
            maxSynapsesPerSegment     = self.tmParams["maxSynapsesPerSegment"]
        )
        self.tm_info = Metrics( [self.tm.numberOfCells()], 999999999 )

        self.anomaly_history = AnomalyLikelihood(self.parameters["anomaly"]["period"])

        self.predictor = Predictor( steps=[1, 5], alpha=self.parameters["predictor"]['sdrc_alpha'] )
        self.predictor_resolution = 1
        

    def algorithm(self, input, count, plotProgress=False):
        record = input
        

        # Iterate through every datum in the dataset, record the inputs & outputs.

        # for count, record in enumerate(records):

        # Convert dite strng into Python date object.
        # dateString = datetime.strptime(record[0],"%H:%M:%S.%f")
        dateString = datetime.fromtimestamp(record[0])
        # Convert data value string into float.
        networkFlow = float(record[1])
        self.inputs.append(networkFlow)

        # Call the encoders to create bit representations for each value.  These are SDR objects.
        dateBits        = self.dateEncoder.encode(dateString)
        networkFlowBits = self.scalarEncoder.encode(networkFlow)

        # Concatenate all these encodings into one large encoding for Spatial Pooling.
        encoding = SDR( self.encodingWidth ).concatenate([networkFlowBits, dateBits])
        self.enc_info.addData( encoding )

        # Create an SDR to represent active columns, This will be populated by the
        # compute method below. It must have the same dimensions as the Spatial Pooler.
        activeColumns = SDR( self.sp.getColumnDimensions() )

        # Execute Spatial Pooling algorithm over input space.
        self.sp.compute(encoding, True, activeColumns)
        self.sp_info.addData( activeColumns )

        # Execute Temporal Memory algorithm over active mini-columns.
        self.tm.compute(activeColumns, learn=True)
        self.tm_info.addData( self.tm.getActiveCells().flatten() )

        # Predict what will happen, and then train the predictor based on what just happened.
        pdf = self.predictor.infer( self.tm.getActiveCells() )
        for n in (1, 5):
            if pdf[n]:
                self.predictions[n].append( np.argmax( pdf[n] ) * self.predictor_resolution )
            else:
                self.predictions[n].append(float('nan'))
                
        self.anomalies.append( self.tm.anomaly )
        self.anomaly_value = self.tm.anomaly
        anomalyLikelihood = self.anomaly_history.anomalyProbability(record,self.tm.anomaly)
        self.anomalyProb.append(anomalyLikelihood)

        self.predictor.learn(count, self.tm.getActiveCells(), int(networkFlow / self.predictor_resolution))


        """
        # Print information & statistics about the state of the HTM.
        print("Encoded Input", enc_info)
        print("")
        print("Spatial Pooler Mini-Columns", sp_info)
        print(str(sp))
        print("")
        print("Temporal Memory Cells", tm_info)
        print(str(tm))
        print("")
        """

        

        """
        # Calculate the predictive accuracy, Root-Mean-Squared
        accuracy         = {1: 0, 5: 0}
        accuracy_samples = {1: 0, 5: 0}

        for idx, inp in enumerate(inputs):
            for n in predictions: # For each [N]umber of time steps ahead which was predicted.
            val = predictions[n][ idx ]
            if not math.isnan(val):
                accuracy[n] += (inp - val) ** 2
                accuracy_samples[n] += 1
        for n in sorted(predictions):
            accuracy[n] = (accuracy[n] / accuracy_samples[n]) ** .5
            print("Predictive Error (RMS)", n, "steps ahead:", accuracy[n])

        # Show info about the anomaly (mean & std)
        print("Anomaly Mean", np.mean(anomaly))
        print("Anomaly Std ", np.std(anomaly))
        """
    def shift_predictions(self):
        # Shift the predictions so that they are aligned with the input they predict.
        for n_steps, pred_list in self.predictions.items():
            for x in range(n_steps):
                pred_list.insert(0, float('nan'))
                pred_list.pop()


    def plot(self):  
        # Plot the Predictions and Anomalies.
        plt.subplot(2,1,1)
        plt.title("Predictions")
        plt.xlabel("Time")
        plt.ylabel("Network Traffic Flow")
        plt.plot(np.arange(len(self.inputs)), self.inputs, 'red',
                np.arange(len(self.inputs)), self.predictions[1], 'blue',
                np.arange(len(self.inputs)), self.predictions[5], 'green',)
        plt.legend(labels=('Input', '1 Step Prediction, Shifted 1 step', '5 Step Prediction, Shifted 5 steps'))

        plt.subplot(2,1,2)
        plt.title("Anomaly Score")
        plt.xlabel("Time")
        plt.ylabel("Network Traffic Flow")
        inputs = np.array(self.inputs) / max(self.inputs)
        plt.plot(np.arange(len(inputs)), inputs, 'black',
                np.arange(len(inputs)), self.anomalies, 'blue',
                np.arange(len(inputs)), self.anomalyProb, 'red',)
        plt.legend(labels=('Input', 'Instantaneous Anomaly', 'Anomaly Likelihood'))
        plt.show()


    def output_df(self):
        header_row = [
                    'timestamp', 'network_flow', 'first_prediction', 'five_prediction', 
                    'anomaly_score', 'anomaly_likelihood'
                ]
        results = pd.DataFrame(columns=header_row)
        first_predictions = self.predictions[1]
        five_predictions = self.predictions[5]
        # n_predictions = self.predictions[n]
        for i in range(self.input_len):
            data = self.input[i]
            output_row = [data[0],data[1],first_predictions[i], five_predictions[i],self.anomaly[i],self.anomalyProb[i]]
            new_result = pd.DataFrame([output_row], columns=header_row)
            new_results = pd.concat([results, new_result], axis=0)
            results = new_results
        
        return results

    def detect_anomaly(self, threshold=0.5):
        found =  False
        if self.anomaly_value > threshold:
            found = True
        return found
