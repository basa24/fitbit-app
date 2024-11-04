import subprocess
import os
import signal
def find_and_kill_port(port):
    try:
        
        result = subprocess.check_output(f"netstat -ano | findstr :{port}", shell=True).decode()
        lines = result.strip().split('\n')
        pids = {line.strip().split()[-1] for line in lines if "LISTENING" in line}
        
        for pid in pids:
           
            subprocess.run(f"taskkill /PID {pid} /F", shell=True)
            print(f"process {pid} using port {port} has been killed.")
    except subprocess.CalledProcessError as e:
        print(f"no process found using port {port}.")
    except Exception as e:
        print(f"an error occurred: {str(e)}")

def application_exit_handler():
    port = 5000  
    find_and_kill_port(port)
    print("application is closing, and the port has been freed.")


application_exit_handler()
