### HTTP log monitoring console program
### Author : Yu Liu

Please read the attached writeup.pdf for more information and test demonstrations.

#### Quick Start


1. Required python packages: dateutils, flask, pandas, numpy, json 
2. ```python logger.py``` to start the log generation (for test data)
3. ```python server.py --port PORT --files FILESTRING``` to start running the server, 
log file name pattern can be changed here from the `files` argument (use bash like pattern matching)
4. open the page at the port to see results
