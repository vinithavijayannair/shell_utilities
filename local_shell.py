import pexpect
import subprocess
import sys

# Local shell command execution
def shell(command, timeout=20):
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, env=os.environ)
        try:
            out, err = process.communicate(timeout=timeout)
            out = out or bytes("", "utf-8")
            err = err or bytes("", "utf-8")
            if process.returncode != 0:
                return (
                    "Output: %s\n Error: %s"
                    % (out.decode("utf-8").strip() or "None", err.decode("utf-8").strip() or "None"),
                    process.returncode,
                )
            return (out.decode("utf-8").strip(), process.returncode)
        except subprocess.TimeoutExpired:
            print("Timed out during: %s" % command)
            return ("Timeout", process.returncode)
    except:
        print("Couldn't open process: %s" % command)
        print(sys.exc_info())
        return (None, -1)
    

# Interact with a shell to provide input as prompted
def interactive_shell(cmd, inputdata, timeout):
    '''
    This function will spawn a command and then pass the parameters after validating if the
    expected values are sent in order. Finally closes the process
    '''
    p = pexpect.spawn(cmd)
    p.timeout = timeout

    for i in range(len(inputdata)):
        index = p.expect([inputdata[i][0], pexpect.EOF, pexpect.TIMEOUT])
        if index == 0:
            p.sendline(inputdata[i][1])
        else:
            print('Expected = %s, Actual = %s' %(inputdata[i][0], p.before))
            p.close(force=True)
            print('The isalive()=%s' % p.isalive())
            return False

    p.expect([pexpect.EOF, pexpect.TIMEOUT])
    if index == 0:
        print('Shell output = %s' % p.before)
        if not p.isalive():
            return True
        else:
            p.close(force=True)
            print('The process status: isalive()=%s' % p.isalive())
            return False
    else:
        print('Expected = EOF, Actual = %s' % p.after)
        return False
