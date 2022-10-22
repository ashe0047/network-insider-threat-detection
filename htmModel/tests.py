from django.test import TestCase
from htmModel.htm_model import HTM
import os
import csv
# Create your tests here.

class HTMTestCase(TestCase):
    def setUp(self):
        # Read the input file.
    
        self.records = []
        _EXAMPLE_DIR = os.path.dirname(os.path.abspath(__file__))
        _INPUT_FILE_PATH = os.path.join(_EXAMPLE_DIR, "networkTraffic.csv")
        with open(_INPUT_FILE_PATH, "r") as fin:
            reader = csv.reader(fin)
            next(reader)
            next(reader)
            next(reader)
            for record in reader:
                self.records.append(record)

        self.htm = HTM()

        
    def test_htm_output(self):
        output_isEmpty = False
        output_isIncorrect = False

        self.count = 0

        for each in self.records:
            self.htm.algorithm(each, self.count)
            self.count+=1

        outputs = self.htm.output_df(self.records)

        for output in outputs:
            if output[2] is  None:
                output_isEmpty = True

            elif output[3] is None:
                output_isIncorrect = True
        
        self.assertEqual(len(outputs), len(self.records))
        self.assertEqual(output_isEmpty, False)
        self.assertEqual(output_isIncorrect, False)



    def test_htm_prediction(self):
        prediction_isEmpty = False
        lst = [["20:01:11.524597",150.0],
               ["20:01:12.524598",220.0],
               ["20:01:13.525076",127.0],
               ["20:01:13.525079",187.0],
               ["20:01:14.525453",114.0]]

        for each in lst:
            self.htm.algorithm(each, self.count)
            self.count+=1

        for n in (1, 5):
            if not self.htm.predictions[n]:
                prediction_isEmpty = True

        prediction = self.htm.predictions[n]
        print(prediction[-5:])

        self.assertEqual(prediction_isEmpty, False)


    def test_htm_anomaly(self):
        anomaly_isEmpty = False
        anomaly_isIncorrect = False
        lst = [["20:01:11.524597",150.0],
               ["20:01:12.524598",220.0],
               ["20:01:13.525076",127.0],
               ["20:01:13.525079",187.0],
               ["20:01:14.525453",114.0]]

        for each in lst:
            self.htm.algorithm(each, self.count)
            self.count+=1

        if not self.htm.anomalies:
            anomaly_isEmpty = True

        for anomaly in self.htm.anomalies:
            if (anomaly >= 0.0 and anomaly <= 1.0) == False:
                anomaly_isIncorrect = True

        print(self.htm.anomalies[-5:])
        self.assertEqual(anomaly_isEmpty, False)
        self.assertEqual(anomaly_isIncorrect, False)


    def test_detect_anomaly(self):
        """Test whether it detect the anomaly"""
        threshold = 0.95
        anomaly_scores = self.htm.anomalies[-10:]
        anomaly_isDetected = False

        for anomaly_score in anomaly_scores:
            if self.htm.detect_anomaly(anomaly_score,threshold=threshold) ==  True:
                anomaly_isDetected = True

        print(anomaly_scores)
        self.assertEqual(anomaly_isDetected, True)