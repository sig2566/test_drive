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
        return True
            
    def chk_booted_next_partition(self, res_list):
        parse= re.compile('\[(r.*)\].*booted')
        for out_str in res_list:
            m= parse.search(out_str)
            if m:
                test_drive.print_log('Found boot partition ' + m.group(1))
                return m.group(1)
        return ''
                    
    
    def rauc_swupdate_test_action(self):
        self.sw_update_upload()
        self.CommonSetup()
        self.exec_target.run_cmd('cd /opt/uep')
        res_list= self.exec_target.run_cmd('rauc status')
        swpartition= self.chk_booted_next_partition(res_list)
        if swpartition=='':
            test_drive.print_log('Booted partition was not found')
            return False
        self.exec_target.run_cmd('rauc install swupdate.raucb')
        res= self.reboot_test()
        if res == False:
            test_drive.print_log('Reboot of server was failed')
            return False
        self.CommonSetup()
        res_list= self.exec_target.run_cmd('rauc status')
        swpartition1= self.chk_booted_next_partition(res_list)
        self.exec_target.close_connection()
        if swpartition1 == swpartition :
            test_drive.print_log('Swap to new partition was failed')
            return False
        
        test_drive.print_log("rauc test was passes")
        return True

    def sw_update_upload(self):
        self.CommonSetup()
        self.exec_target.run_cmd('cd /opt/uep')
        self.exec_target.run_cmd('tftp ' + self.exec_host.ip + ' -g -r swupdate.raucb')                
        self.exec_target.close_connection()
        return True
    
    def rauc_sw_update_install(self):

        self.CommonSetup()
        self.exec_target.run_cmd('cd /opt/uep')
        res_list= self.exec_target.run_cmd('rauc status')
        swpartition= self.chk_booted_next_partition(res_list)
        if swpartition=='':
            test_drive.print_log('Booted partition was not found')
            return False
        test_drive.print_log("Current partition: "+ swpartition)
        self.exec_target.run_cmd('rauc install swupdate.raucb')
        return True
        #self.exec_target.close_connection()
        

exec_target= test_drive.ExecTarget()                
test_handler = ENOS_main_handler(exec_target)
#exec_target.add_parent_class_callback(test_handler)
xml_handler= test_drive.XML_handler(test_handler)
test_drive.test_processing(xml_handler)
            
    