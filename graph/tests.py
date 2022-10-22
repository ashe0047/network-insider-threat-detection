from django.test import TestCase
from graph.consumers import GraphConsumer
from webApp.settings import BASE_DIR
from scapy.all import*
from scapy.layers.inet import *
import datetime as dt
import pandas as pd
from channels.testing.websocket import WebsocketCommunicator



# Create your tests here.
class GraphConsumerWhiteBoxTest(TestCase):
    def setUp(self) -> None:
        self.gc = GraphConsumer()
        data_dir = str(BASE_DIR/'dataset/test2.pcap')
        self.data = rdpcap(data_dir)
        self.fields = self.gc.field_gen()
        
    def test_packet_processor(self):
        #path 1 test
        test_fields = {
            'ip_fields': [],
            'tcp_fields': []
        }
        pkt = self.data[UDP][0]
        row = self.gc.pkt_processor(pkt, test_fields)

        self.assertEqual(len(row), 0)

        #path 2 test
        pkt = self.data[TCP][0]
        test_fields = {
            'ip_fields': [],
            'tcp_fields': []
        }

        row = self.gc.pkt_processor(pkt, test_fields)
        exp_output = [pkt.time, len(pkt[TCP].payload), pkt[TCP].payload.original]
        self.assertEqual(row, exp_output)

        #path test 3
        pkt = self.data[TCP][0]
        test_fields['tcp_fields'] = ['tcp_options']
        row = self.gc.pkt_processor(pkt, test_fields)
        exp_output = [pkt.time, len(pkt[TCP].fields['options']), len(pkt[TCP].payload), pkt[TCP].payload.original]
        
        self.assertEqual(row,  exp_output)

        #path test 4
        pkt = self.data[TCP][0]
        test_fields['tcp_fields'] = ['tcp_flags']
        row = self.gc.pkt_processor(pkt, test_fields)
        exp_output = [pkt.time, pkt[TCP].fields['flags'], len(pkt[TCP].payload), pkt[TCP].payload.original]
        
        self.assertEqual(row, exp_output)

        #path test 5
        pkt = self.data[TCP][0]
        test_fields['tcp_fields'] = ['sport','dport',
                                        'seq',
                                        'ack',
                                        'dataofs',
                                        'reserved',
                                        'window',
                                        'urgptr']
        row = self.gc.pkt_processor(pkt, test_fields)
        exp_output = [pkt.time]
        exp_output += [pkt[TCP].fields[field] for field in ['sport','dport',
                                        'seq',
                                        'ack',
                                        'dataofs',
                                        'reserved',
                                        'window',
                                        'urgptr']]
        exp_output += [len(pkt[TCP].payload), pkt[TCP].payload.original]
       
        self.assertEqual(row, exp_output)

        #path test 6
        pkt = self.data[TCP][0]
        test_fields['tcp_fields'] = ['tcp_chksum']
        row = self.gc.pkt_processor(pkt, test_fields)
        exp_output = [pkt.time, pkt[TCP].fields['chksum'], len(pkt[TCP].payload), pkt[TCP].payload.original]

        self.assertEqual(row, exp_output)

        #path test 7
        pkt = self.data[TCP][0]
        test_fields['ip_fields'] = ['ip_chksum']
        test_fields['tcp_fields'] = []
        row = self.gc.pkt_processor(pkt, test_fields)
        exp_output = [pkt[IP].fields['chksum'], pkt.time, len(pkt[TCP].payload), pkt[TCP].payload.original]

        self.assertEqual(row, exp_output)

        #path test 8
        pkt = self.data[TCP][0]
        test_fields['ip_fields'] = ['ip_flags']
        row = self.gc.pkt_processor(pkt, test_fields)
        exp_output = [pkt[IP].fields['flags'], pkt.time, len(pkt[TCP].payload), pkt[TCP].payload.original]

        self.assertEqual(row, exp_output)

        #path test 9
        pkt = self.data[TCP][0]
        test_fields['ip_fields'] = ['version',
                                        'ihl',
                                        'tos',
                                        'len',
                                        'id',
                                        'frag',
                                        'ttl',
                                        'proto',
                                        'src',
                                        'dst']
        row = self.gc.pkt_processor(pkt, test_fields)
        exp_output = [pkt[IP].fields[field] for field in ['version',
                                        'ihl',
                                        'tos',
                                        'len',
                                        'id',
                                        'frag',
                                        'ttl',
                                        'proto',
                                        'src',
                                        'dst']]
        exp_output += [pkt.time]
        exp_output += [len(pkt[TCP].payload), pkt[TCP].payload.original]

        self.assertEqual(row, exp_output)

        #path test 10
        pkt = self.data[TCP][0]
        test_fields['ip_fields'] = ['ip_options']
        row = self.gc.pkt_processor(pkt, test_fields)
        exp_output = [len(pkt[IP].fields['options']), pkt.time, len(pkt[TCP].payload), pkt[TCP].payload.original]

        self.assertEqual(row, exp_output)


    def test_df_add_row(self):
        #path 1 test
        pkt_df = pd.DataFrame(columns=self.fields['df_fields'])
        pkt_select = []
        for ind in range(len(self.data[TCP])):
            pkt_processed_1 = self.gc.pkt_processor(self.data[TCP][ind], self.fields)
            pkt_processed_2 = self.gc.pkt_processor(self.data[TCP][ind+1], self.fields)
            time1 = dt.datetime.fromtimestamp(float(self.data[TCP][ind].time)).isoformat(timespec='milliseconds')
            time2 = dt.datetime.fromtimestamp(float(self.data[TCP][ind+1].time)).isoformat(timespec='milliseconds')

            if time1 == time2:
                pkt_select.append(pkt_processed_1)
                pkt_select.append(pkt_processed_2)
                break

        prev_time = None
        for i in pkt_select:
            pkt_df, curr_time = self.gc.df_add_row(i, pkt_df, prev_time)
            prev_time = curr_time
        print(pkt_select)
        self.assertEqual(pkt_df.shape[0], 2)

        #path 2 test
        pkt_df = pd.DataFrame(columns=self.fields['df_fields'])
        pkt_select = []
        for ind in range(len(self.data[TCP])):
            pkt_processed_1 = self.gc.pkt_processor(self.data[TCP][ind], self.fields)
            pkt_processed_2 = self.gc.pkt_processor(self.data[TCP][ind+1], self.fields)
            time1 = dt.datetime.fromtimestamp(float(self.data[TCP][ind].time)).isoformat(timespec='milliseconds')
            time2 = dt.datetime.fromtimestamp(float(self.data[TCP][ind+1].time)).isoformat(timespec='milliseconds')

            if time1 != time2:
                pkt_select.append(pkt_processed_1)
                pkt_select.append(pkt_processed_2)
                break

        prev_time = None
        for i in pkt_select:
            pkt_df, curr_time = self.gc.df_add_row(i, pkt_df, prev_time)
            prev_time = curr_time

        print(pkt_select)
        self.assertEqual(pkt_df.shape[0], 1)


# from staticfg import CFGBuilder
# cfg = CFGBuilder().build_from_file('GraphConsumer', './consumers.py')
# cfg.build_visual('GraphConsumerCFG', 'png')

