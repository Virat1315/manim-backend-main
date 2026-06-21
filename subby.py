import subprocess
try:
    command = "manim -pql manimcode.py SphereAnimation"
    result = subprocess.run(
                command, 
                shell=True, 
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10  # 1 minute timeout
            )
            
    print(f"Manim execution output: {result.stdout}")

except subprocess.TimeoutExpired as e:
    print(f"Command timed out after {e.timeout} seconds")
    print(f"Partial stdout: {e.stdout if e.stdout else 'None'}")
    print(f"Partial stderr: {e.stderr if e.stderr else 'None'}")
    
except subprocess.CalledProcessError as e:
    print(f"Failed to run Manim: \nstdout={e.stdout}\nstderr={e.stderr}")
    print(f"Command '{e.cmd}' returned non-zero exit status {e.returncode}")