```python
import os
import sys
from test_functions import run_all_tests
from test_functions import print_test_result

PROXY_URL = os.getenv('PROXY_URL')
PROXY_API_KEY = os.getenv('PROXY_API_KEY')

if not PROXY_URL or not PROXY_API_KEY:
    print("Missing required environment variables: PROXY_URL and/or PROXY_API_KEY")
    sys.exit(1)

test_results = run_all_tests(PROXY_URL, PROXY_API_KEY)

print_test_result(test_results)

exit_code = 0 if test_results['success'] else 1
sys.exit(exit_code)
```