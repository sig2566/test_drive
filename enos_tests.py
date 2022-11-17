import re
import test_drive
from conda.common._logic import FALSE
#from conda.common._logic import FALSE

class ENOS_main_handler(test_drive.MainHandler):
    def __init__(self, exec_target):
        super().__init__(exec_target)
         
    def get_current_partition(self):
        self.CommonSetup()        
        self.exec_target.close_connection()
            
    def chk_booted_next_partition(self, res_list):
        parse= re.compile('\[(r.*)\].*booted')
        for out_str in res_list:
            m= parse.search(out_str)
            if m:
                print('Found boot partition ' + m.group(1))
                return m.group(1)
        return ''
                    
    
    def rauc_swupdate_test_action(self):
        num=  int(self.iterations)
        while(num>0):
            num-=1
            self.CommonSetup()
            self.exec_target.run_cmd('cd /opt/uep')
            self.exec_target.run_cmd('tftp ' + self.exec_host.ip + ' -g -r swupdate.raucb')                
            res_list= self.exec_target.run_cmd('rauc status')
            swpartition= self.chk_booted_next_partition(res_list)
            if swpartition=='':
                print('Booted partition was not found')
                return False
            self.exec_target.run_cmd('rauc install swupdate.raucb')
            self.exec_target.close_connection()
            res= self.reboot_test()
            if res == False:
                print('Reboot of server was failed')
                return False
            self.CommonSetup()
            res_list= self.exec_target.run_cmd('rauc status')
            swpartition1= self.chk_booted_next_partition(res_list)
            self.exec_target.close_connection()
            if swpartition1 == swpartition :
                print('Swap to new partition was failed')
                return False
            
        print("rauc test was passes")
        return True

exec_target= test_drive.ExecTarget()                
test_handler = ENOS_main_handler(exec_target)
#exec_target.add_parent_class_callback(test_handler)
xml_handler= test_drive.XML_handler(test_handler)
test_drive.test_processing(xml_handler)
            
    