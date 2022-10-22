from math import isnan
import json
from channels.generic.websocket import WebsocketConsumer
import numpy as np
import pandas as pd
from scapy.all import *
from scapy.layers.inet import IP, TCP, UDP 
from webApp.settings import BASE_DIR
import htmModel.htm_model as htm

class GraphConsumer(WebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        #variables setup
        self.htm_model = htm.HTM()
        self.data_dir = str(BASE_DIR/'dataset/test2.pcap')
        self.data = PcapReader(self.data_dir)
        self.pkt_df_time = pd.DataFrame(columns=self.field_gen()['df_fields'])
        self.pkt_df_others = pd.DataFrame(columns=self.field_gen()['df_fields'])
        self.prev_sec = None
        self.message = {}

    def connect(self):
        self.accept()
        for count, pkt in enumerate(self.data):
            self.message = {}
            processed_pkt = self.pkt_processor(pkt, self.field_gen())
            if len(processed_pkt) != 0:

                #Run HTM Algorithm
                self.message['anomaly_detected'] = self.run_htm(processed_pkt, count, self.htm_model)
                time_msg = np.arange(len(self.htm_model.inputs))
                self.message['prediction_plot'] = {
                    "time": time_msg.tolist(),
                    "data": self.htm_model.inputs,
                    "pred_1": list(map(float,[x for x in self.htm_model.predictions[1] if isnan(x) == False])),
                    "pred_5": list(map(float,[x for x in self.htm_model.predictions[5] if isnan(x) == False]))
                }
                time_msg = np.arange(len(self.htm_model.inputs))
                data_msg = np.array(self.htm_model.inputs)/max(self.htm_model.inputs)
                self.message['anomaly_plot'] = {
                    'time': time_msg.tolist(),
                    'data': [x for x in data_msg.tolist() if isnan(x) == False],
                    'anomalies': list(map(float,[x for x in self.htm_model.anomalies if isnan(x) == False])),
                    'anomaly_prob': list(map(float,[x for x in self.htm_model.anomalyProb if isnan(x) == False]))
                }

                #graph data
                curr_df, curr_sec = self.df_add_row(processed_pkt, self.pkt_df_time, 'time', self.prev_sec)
                self.pkt_df_time = curr_df

                self.pkt_df_others = self.df_add_row(processed_pkt, self.pkt_df_others, 'others')

                #port df
                port_df = self.pkt_df_others.groupby(['dport'], as_index=False)
                port_df = port_df.agg(users=pd.NamedAgg('src', 'count'))
                if port_df.shape[0] > 10:
                    port_df = port_df.iloc[port_df.shape[0]-10:, :]
                self.message['port'] = {
                    'users': port_df['users'].to_list(),
                    'dport': port_df['dport'].to_list()
                }
                self.send(json.dumps(self.message))


                #check if processed_pkt in same interval
                if (curr_sec != self.prev_sec and self.prev_sec is not None):
                    curr_df['received_time'] = curr_df['received_time'].map(lambda x: x.to_pydatetime().isoformat(timespec='milliseconds'))
                    #traffic volume
                    vol_df = curr_df.groupby(['received_time'], as_index=False)
                    vol_df = vol_df.agg(total_payload=pd.NamedAgg('payload_size', 'sum'))
                    self.message['traffic_vol'] = vol_df.to_dict(orient='records')
                    #unique users
                    user_df = curr_df.groupby(['received_time'], as_index=False)
                    user_df = user_df.agg(users=pd.NamedAgg('src', 'count'))
                    self.message['users'] = user_df.to_dict(orient='records')
                    
                    self.send(json.dumps(self.message))

                    #reset variables
                    self.prev_sec = None
                    self.pkt_df_time = pd.DataFrame(columns=self.field_gen()['df_fields'])
                
                self.prev_sec = curr_sec
                

        self.message = {}
        self.pkt_df_time['received_time'] = self.pkt_df_time['received_time'].map(lambda x: x.to_pydatetime().isoformat(timespec='milliseconds'))
        
        #traffic volume
        vol_df = self.pkt_df_time.groupby(['received_time'], as_index=False)
        vol_df = vol_df.agg(total_payload=pd.NamedAgg('payload_size', 'sum'))
        self.message['traffic_vol'] = vol_df.to_dict(orient='records')

        #unique users
        user_df = self.pkt_df_time.groupby(['received_time'], as_index=False)
        user_df = user_df.agg(users=pd.NamedAgg('src', 'count'))
        self.message['users'] = user_df.to_dict(orient='records')

        self.send(json.dumps(self.message))
        self.close()


    def run_htm (self, pkt, count, htm):
        #input processing for htm
        df_row = pd.DataFrame([pkt], columns=self.field_gen()['df_fields'])
        df_row = df_row.loc[:, df_row.columns!='raw_payload']
        json_row = json.loads(df_row.to_json(orient='records'))[0]
        htm_input = [json_row['received_time'], json_row['payload_size']]

        #run htm algorithm 
        htm.algorithm(htm_input, count)
        # print(htm.anomalies)
        anomaly = False if len(htm.anomalies) < 5000 else htm.detect_anomaly(0.95)
        return anomaly
    
    def field_gen(self):
        #field names for IP,TCP,UDP
        tcp_fields = ['tcp_options' if field.name == 'options' else 'tcp_chksum' if field.name == 'chksum' else 'tcp_flags' if field.name == 'flags' else field.name for field in TCP().fields_desc ]
        udp_fields = [field.name for field in UDP().fields_desc]
        ip_fields = ['ip_options' if field.name == 'options' else 'ip_chksum' if field.name == 'chksum' else 'ip_flags' if field.name == 'flags' else field.name for field in IP().fields_desc]

        #all fields
        df_fields = ip_fields + ['received_time'] + tcp_fields + ['payload_size'] + ['raw_payload']
        all_fields = {
            'df_fields': df_fields,
            'tcp_fields': tcp_fields,
            'ip_fields': ip_fields
        }
        return all_fields

    def pkt_processor(self, pkt, fields): 
        row_val = []
        
        if isinstance(pkt.payload.payload, TCP):
            #add value of each ip fields
            for field in fields['ip_fields']:
                if field == 'ip_options':
                    row_val.append(len(pkt[IP].fields['options']))
                elif field == 'ip_chksum':
                    row_val.append(pkt[IP].fields['chksum'])
                elif field == 'ip_flags':
                    row_val.append(pkt[IP].fields['flags'])
                else:
                    row_val.append(pkt[IP].fields[field])
            
            #add time value
            row_val.append(pkt.time)

            #add value of each tcp fields
            tcp_filt = type(pkt[IP].payload)
            for field in fields['tcp_fields']:
                try:
                    if field == 'tcp_options':
                        row_val.append(len(pkt[tcp_filt].fields['options']))
                    elif field == 'tcp_chksum':
                        row_val.append(pkt[tcp_filt].fields['chksum'])
                    elif field == 'tcp_flags':
                        row_val.append(pkt[tcp_filt].fields['flags'])
                    else:
                        row_val.append(pkt[tcp_filt].fields[field])
                except:
                    row_val.append(None)
            
            #add raw payload
            row_val.append(len(pkt[tcp_filt].payload))
            row_val.append(pkt[tcp_filt].payload.original)
        return row_val

    def df_add_row(self, row, df, group_attr, prev_sec=None):
        df_row = pd.DataFrame([row], columns=self.field_gen()['df_fields'])
        df_row.reset_index(inplace=True)
        if group_attr == 'time':
            df_row['received_time'] = pd.to_datetime(pd.to_numeric(df_row['received_time']), unit='s', utc=True)
            df_row['received_time'].dt.tz_convert('Asia/Singapore')

            if df_row['received_time'][0].to_pydatetime().isoformat(timespec='milliseconds') == prev_sec or prev_sec == None:
                df = pd.concat([df, df_row], axis=0)
            re_val = (df, df_row['received_time'][0].to_pydatetime().isoformat(timespec='milliseconds'))
        
        elif group_attr == 'others':
            re_val = pd.concat([df, df_row], axis=0)


        return re_val

        
    