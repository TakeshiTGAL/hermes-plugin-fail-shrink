"""One row per failure-log shape the parsers must tell apart.

The pytest rows replace the location heuristics. Every id is executed by
test_input_kinds_cover_every_row.
"""

PYTEST_ARGV = ["python", "-m", "pytest", "-q"]

ROWS = [
    {
        "id": "pytest-relative-two",
        "dialect": "pytest",
        "argv": PYTEST_ARGV,
        "log": """
=================================== FAILURES ===================================
__________________________________ test_one ___________________________________

    def test_one():
>       assert ("stale one") == ("fresh one")
E       AssertionError: assert 'stale one' == 'fresh one'

test_auth.py:2: AssertionError
__________________________________ test_two ___________________________________

    def test_two():
>       assert ("stale two") == ("fresh two")
E       AssertionError: assert 'stale two' == 'fresh two'

test_auth.py:5: AssertionError
=========================== short test summary info ============================
FAILED test_auth.py::test_one - AssertionError: assert 'stale one' == 'fresh one'
FAILED test_auth.py::test_two - AssertionError: assert 'stale two' == 'fresh two'
============================== 2 failed in 0.01s ===============================
""",
                "expect": [
            ('test_auth.py', 0, 'test_one', "AssertionError: assert 'stale one' == 'fresh one'"),
            ('test_auth.py', 0, 'test_two', "AssertionError: assert 'stale two' == 'fresh two'"),
        ],
        "rerun": "python -m pytest test_auth.py -k 'test_one or test_two'",
    },
    {
        "id": "pytest-helper-frame",
        "dialect": "pytest",
        "argv": ["python", "-m", "pytest", "test_real.py"],
        "log": """
=================================== FAILURES ===================================
________________________________ test_real_bug _________________________________

    def test_real_bug():
>       check(0)

test_real.py:5: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    def check(value):
>       assert value == 1
E       AssertionError

helper.py:2: AssertionError
=========================== short test summary info ============================
FAILED test_real.py::test_real_bug - AssertionError
============================== 1 failed in 0.01s ===============================
""",
                "expect": [
            ('test_real.py', 0, 'test_real_bug', 'AssertionError'),
        ],
        "rerun": 'python -m pytest test_real.py -k test_real_bug',
        "anchor_prefix": 'FAILED test_real.py::test_real_bug - AssertionError',
    },
    {
        "id": "pytest-captured-stale",
        "dialect": "pytest",
        "argv": ["python", "-m", "pytest", "test_prints_old.py"],
        "log": """
=================================== FAILURES ===================================
_____________________________ test_prints_old_log ______________________________

>       assert 1 == 2
E       assert 1 == 2

test_prints_old.py:4: AssertionError
----------------------------- Captured stdout call -----------------------------
=================================== FAILURES ===================================
______________________________ test_token_expired ______________________________
E       AssertionError: stale
tests/test_auth.py:167: AssertionError
=========================== short test summary info ============================
FAILED tests/test_auth.py::test_token_expired - AssertionError: stale
============================== 1 failed in 0.01s ===============================
=========================== short test summary info ============================
FAILED test_prints_old.py::test_prints_old_log - assert 1 == 2
============================== 1 failed in 0.02s ===============================
""",
                "expect": [
            ('test_prints_old.py', 0, 'test_prints_old_log', 'assert 1 == 2'),
        ],
        "rerun": 'python -m pytest test_prints_old.py -k test_prints_old_log',
        "absent_names": ["test_token_expired"],
    },
    {
        "id": "pytest-same-name-printed-before-summary",
        "dialect": "pytest",
        "argv": ["python", "-m", "pytest", "test_prints_old.py"],
        "log": """
_____________________________ test_prints_old_log ______________________________
E       assert 0 == 1
old.py:1: AssertionError
=========================== short test summary info ============================
FAILED old.py::test_prints_old_log - assert 0 == 1
============================== 1 failed in 0.01s ===============================
=================================== FAILURES ===================================
_____________________________ test_prints_old_log ______________________________
>       assert 1 == 2
E       assert 1 == 2
test_prints_old.py:4: AssertionError
=========================== short test summary info ============================
FAILED test_prints_old.py::test_prints_old_log - assert 1 == 2
============================== 1 failed in 0.02s ===============================
""",
                "expect": [
            ('test_prints_old.py', 0, 'test_prints_old_log', 'assert 1 == 2'),
        ],
        "rerun": 'python -m pytest test_prints_old.py -k test_prints_old_log',
        "absent_files": ["old.py"],
    },
    {
        "id": "pytest-dashs-same-name",
        "dialect": "pytest",
        "argv": ["python", "-m", "pytest", "-s", "test_same.py"],
        "log": """
=================================== FAILURES ===================================
______________________________ test_token_expired ______________________________
E       AssertionError: assert 'stale token' == 'fresh token'
tests/test_auth.py:167: AssertionError
----------------------------- Captured stdout call -----------------------------
old capture
=========================== short test summary info ============================
FAILED tests/test_auth.py::test_token_expired - AssertionError: assert 'stale token' == 'fresh token'
============================== 1 failed in 0.01s ===============================
=================================== FAILURES ===================================
______________________________ test_token_expired ______________________________
>       assert 1 == 2
E       assert 1 == 2
test_same.py:3: AssertionError
=========================== short test summary info ============================
FAILED test_same.py::test_token_expired - assert 1 == 2
============================== 1 failed in 0.02s ===============================
""",
                "expect": [
            ('test_same.py', 0, 'test_token_expired', 'assert 1 == 2'),
        ],
        "rerun": 'python -m pytest test_same.py -k test_token_expired',
        "absent_files": ["tests/test_auth.py"],
    },
    {
        "id": "pytest-dashs-same-file",
        "dialect": "pytest",
        "argv": ["python", "-m", "pytest", "-s", "test_same.py"],
        "log": """
=================================== FAILURES ===================================
______________________________ test_token_expired ______________________________
E       AssertionError: stale copy
test_same.py:167: AssertionError
=========================== short test summary info ============================
FAILED test_same.py::test_token_expired - AssertionError: stale copy
============================== 1 failed in 0.01s ===============================
=================================== FAILURES ===================================
______________________________ test_token_expired ______________________________
>       assert 1 == 2
E       assert 1 == 2
test_same.py:3: AssertionError
=========================== short test summary info ============================
FAILED test_same.py::test_token_expired - assert 1 == 2
============================== 1 failed in 0.02s ===============================
""",
                "expect": [
            ('test_same.py', 0, 'test_token_expired', 'assert 1 == 2'),
        ],
        "rerun": 'python -m pytest test_same.py -k test_token_expired',
    },
    {
        "id": "pytest-dashs-same-assert",
        "dialect": "pytest",
        "argv": ["python", "-m", "pytest", "-s", "test_same.py"],
        "log": """
=================================== FAILURES ===================================
______________________________ test_token_expired ______________________________
E       assert 1 == 2
test_same.py:167: AssertionError
=========================== short test summary info ============================
FAILED test_same.py::test_token_expired - assert 1 == 2
============================== 1 failed in 0.01s ===============================
=================================== FAILURES ===================================
______________________________ test_token_expired ______________________________
E       assert 1 == 2
test_same.py:3: AssertionError
=========================== short test summary info ============================
FAILED test_same.py::test_token_expired - assert 1 == 2
============================== 1 failed in 0.02s ===============================
""",
                "expect": [
            ('test_same.py', 0, 'test_token_expired', 'assert 1 == 2'),
        ],
        "rerun": 'python -m pytest test_same.py -k test_token_expired',
    },
    {
        "id": "pytest-captured-same-name",
        "dialect": "pytest",
        "argv": ["python", "-m", "pytest", "test_same.py"],
        "log": """
=================================== FAILURES ===================================
______________________________ test_token_expired ______________________________
>       assert 1 == 2
E       assert 1 == 2
test_same.py:3: AssertionError
----------------------------- Captured stdout call -----------------------------
=================================== FAILURES ===================================
______________________________ test_token_expired ______________________________
E       AssertionError: stale
tests/test_auth.py:167: AssertionError
=========================== short test summary info ============================
FAILED tests/test_auth.py::test_token_expired - AssertionError: stale
============================== 1 failed in 0.01s ===============================
=========================== short test summary info ============================
FAILED test_same.py::test_token_expired - assert 1 == 2
============================== 1 failed in 0.02s ===============================
""",
                "expect": [
            ('test_same.py', 0, 'test_token_expired', 'assert 1 == 2'),
        ],
        "rerun": 'python -m pytest test_same.py -k test_token_expired',
        "absent_files": ["tests/test_auth.py"],
    },
    {
        "id": "pytest-captured-same-file",
        "dialect": "pytest",
        "argv": ["python", "-m", "pytest", "test_same.py"],
        "log": """
=================================== FAILURES ===================================
______________________________ test_token_expired ______________________________
>       assert 1 == 2
E       assert 1 == 2
test_same.py:3: AssertionError
----------------------------- Captured stdout call -----------------------------
=================================== FAILURES ===================================
______________________________ test_token_expired ______________________________
E       AssertionError: stale copy
test_same.py:167: AssertionError
=========================== short test summary info ============================
FAILED test_same.py::test_token_expired - AssertionError: stale copy
============================== 1 failed in 0.01s ===============================
=========================== short test summary info ============================
FAILED test_same.py::test_token_expired - assert 1 == 2
============================== 1 failed in 0.02s ===============================
""",
                "expect": [
            ('test_same.py', 0, 'test_token_expired', 'assert 1 == 2'),
        ],
        "rerun": 'python -m pytest test_same.py -k test_token_expired',
    },
    {
        "id": "pytest-captured-same-assert",
        "dialect": "pytest",
        "argv": ["python", "-m", "pytest", "test_same.py"],
        "log": """
=================================== FAILURES ===================================
______________________________ test_token_expired ______________________________
E       assert 1 == 2
test_same.py:3: AssertionError
----------------------------- Captured stdout call -----------------------------
=================================== FAILURES ===================================
______________________________ test_token_expired ______________________________
E       assert 1 == 2
test_same.py:167: AssertionError
=========================== short test summary info ============================
FAILED test_same.py::test_token_expired - assert 1 == 2
============================== 1 failed in 0.01s ===============================
=========================== short test summary info ============================
FAILED test_same.py::test_token_expired - assert 1 == 2
============================== 1 failed in 0.02s ===============================
""",
                "expect": [
            ('test_same.py', 0, 'test_token_expired', 'assert 1 == 2'),
        ],
        "rerun": 'python -m pytest test_same.py -k test_token_expired',
    },
    {
        "id": "pytest-truncated-dashs-different-assert",
        "dialect": "pytest",
        "argv": ["python", "-m", "pytest", "-s", "test_same.py"],
        "log": """
=================================== FAILURES ===================================
______________________________ test_token_expired ______________________________
E       AssertionError: stale copy
test_same.py:167: AssertionError
----------------------------- Captured stdout call -----------------------------
old capture
=================================== FAILURES ===================================
______________________________ test_token_expired ______________________________
E       assert 1 == 2
test_same.py:3: AssertionError
=========================== short test summary info ============================
FAILED test_same.py::test_token_expired - assert 1 == 2
============================== 1 failed in 0.02s ===============================
""",
                "expect": [
            ('test_same.py', 0, 'test_token_expired', 'assert 1 == 2'),
        ],
        "rerun": 'python -m pytest test_same.py -k test_token_expired',
    },
    {
        "id": "pytest-truncated-dashs-same-assert",
        "dialect": "pytest",
        "argv": ["python", "-m", "pytest", "-s", "test_same.py"],
        "log": """
=================================== FAILURES ===================================
______________________________ test_token_expired ______________________________
E       assert 1 == 2
test_same.py:167: AssertionError
----------------------------- Captured stdout call -----------------------------
old capture
=================================== FAILURES ===================================
______________________________ test_token_expired ______________________________
E       assert 1 == 2
test_same.py:3: AssertionError
=========================== short test summary info ============================
FAILED test_same.py::test_token_expired - assert 1 == 2
============================== 1 failed in 0.02s ===============================
""",
                "expect": [
            ('test_same.py', 0, 'test_token_expired', 'assert 1 == 2'),
        ],
        "rerun": 'python -m pytest test_same.py -k test_token_expired',
    },
    {
        "id": "pytest-capture-hides-next-name",
        "dialect": "pytest",
        "argv": PYTEST_ARGV,
        "log": """
=================================== FAILURES ===================================
__________________________________ test_one ___________________________________
E       assert 1 == 0
test_auth.py:2: AssertionError
----------------------------- Captured stdout call -----------------------------
__________________________________ test_two ___________________________________
E       assert 9 == 9
old.py:1: AssertionError
__________________________________ test_two ___________________________________
E       assert 2 == 0
test_auth.py:5: AssertionError
=========================== short test summary info ============================
FAILED test_auth.py::test_one - assert 1 == 0
FAILED test_auth.py::test_two - assert 2 == 0
============================== 2 failed in 0.01s ===============================
""",
                "expect": [
            ('test_auth.py', 0, 'test_one', 'assert 1 == 0'),
            ('test_auth.py', 0, 'test_two', 'assert 2 == 0'),
        ],
        "rerun": "python -m pytest test_auth.py -k 'test_one or test_two'",
        "absent_files": ["old.py"],
    },
    {
        "id": "pytest-dotdot-absolute",
        "dialect": "pytest",
        "argv": ["python", "-m", "pytest", "-q", "/var/work/test_token.py"],
        "log": """
=================================== FAILURES ===================================
______________________________ test_token_expired ______________________________

>       assert 1 == 0
E       assert 1 == 0

/var/work/test_token.py:3: AssertionError
=========================== short test summary info ============================
FAILED ../../../../var/work/test_token.py::test_token_expired - assert 1 == 0
============================== 1 failed in 0.01s ===============================
""",
                "expect": [
            ('../../../../var/work/test_token.py', 0, 'test_token_expired', 'assert 1 == 0'),
        ],
        "rerun": None,
        "block_rerun": True,
    },
    {
        "id": "pytest-dotdot-ambiguous",
        "dialect": "pytest",
        "argv": PYTEST_ARGV,
        "log": """
=================================== FAILURES ===================================
__________________________________ test_one ___________________________________

>       assert 1 == 0
E       assert 1 == 0

/var/other/test_token.py:9: AssertionError
/var/work/test_token.py:3: AssertionError
=========================== short test summary info ============================
FAILED ../test_token.py::test_one - assert 1 == 0
============================== 1 failed in 0.01s ===============================
""",
                "expect": [
            ('../test_token.py', 0, 'test_one', 'assert 1 == 0'),
        ],
        "rerun": None,
        "block_rerun": True,
    },
    {
        "id": "pytest-dotdot-no-absolute",
        "dialect": "pytest",
        "argv": PYTEST_ARGV,
        "log": """
=================================== FAILURES ===================================
______________________________ test_token_expired ______________________________

>       assert 1 == 0
E       assert 1 == 0

work/test_token.py:3: AssertionError
=========================== short test summary info ============================
FAILED ../../test_token.py::test_token_expired - assert 1 == 0
============================== 1 failed in 0.01s ===============================
""",
                "expect": [
            ('../../test_token.py', 0, 'test_token_expired', 'assert 1 == 0'),
        ],
        "rerun": None,
        "block_rerun": True,
    },
    {
        "id": "pytest-dotdot-location",
        "dialect": "pytest",
        "argv": ["python", "-m", "pytest", "-q", "../var/folders/xx/test_token.py"],
        "log": """
=================================== FAILURES ===================================
______________________________ test_token_expired ______________________________

    def test_token_expired():
>       assert 1 == 0
E       assert 1 == 0

../var/folders/xx/test_token.py:2: AssertionError
=========================== short test summary info ============================
FAILED ../var/folders/xx/test_token.py::test_token_expired - assert 1 == 0
============================== 1 failed in 0.01s ===============================
""",
                "expect": [
            ('../var/folders/xx/test_token.py', 0, 'test_token_expired', 'assert 1 == 0'),
        ],
        "rerun": None,
        "block_rerun": True,
    },
    {
        "id": "pytest-summary-only",
        "dialect": "pytest",
        "argv": ["python", "-m", "pytest", "test_token.py"],
        "log": """
=========================== short test summary info ============================
FAILED test_token.py::test_token_expired - assert 1 == 0
============================== 1 failed in 0.01s ===============================
""",
                "expect": [
            ('test_token.py', 0, 'test_token_expired', 'assert 1 == 0'),
        ],
        "rerun": 'python -m pytest test_token.py -k test_token_expired',
    },
    {
        "id": "pytest-no-summary",
        "dialect": None,
        "log": """
=================================== FAILURES ===================================
FAILED tests/test_auth.py::test_token_expired - AssertionError: stale
""",
    },
    {
        "id": "jest-indented-printed-log",
        "dialect": "jest",
        "argv": ["npx", "jest", "auth.test.js"],
        "log": """
FAIL ./auth.test.js
  ● token expired
      > 47 | expect(a).toBe(b);
      at Object.toBe (auth.test.js:47:1)
    console.log
      FAIL ./old.test.js
        ● old token
        at Object.toBe (old.test.js:3:1)
Test Suites: 1 failed, 1 total
""",
                "expect": [
            ('auth.test.js', 0, 'token expired', ''),
        ],
        "absent_names": ["old token"],
        "rerun": "npx jest auth.test.js -t 'token expired'",
    },
    {
        "id": "jest-printed-report-before-live",
        "dialect": "jest",
        "argv": ["npx", "jest", "auth.test.js"],
        "log": """
FAIL ./old.test.js
  ● old token
      at Object.toBe (old.test.js:3:1)
Test Suites: 1 failed, 1 total
FAIL ./auth.test.js
  ● token expired
      > 47 | expect(a).toBe(b);
      at Object.toBe (auth.test.js:47:1)
Test Suites: 1 failed, 1 total
""",
                "expect": [
            ('auth.test.js', 0, 'token expired', ''),
        ],
        "absent_names": ["old token"],
        "absent_files": ["old.test.js"],
        "rerun": "npx jest auth.test.js -t 'token expired'",
    },
    {
        "id": "vitest-banner-ignores-earlier-fail",
        "dialect": "vitest",
        "argv": ["npx", "vitest", "run", "token.test.js"],
        "log": """
 Test Files  1 failed

 FAIL  old.test.js > stale
AssertionError: stale
 ❯ old.test.js:3:1

⎯⎯⎯⎯⎯⎯⎯ Failed Tests 1 ⎯⎯⎯⎯⎯⎯⎯

 FAIL  token.test.js > token expired
AssertionError: assert stale
 ❯ token.test.js:47:4
""",
                "expect": [
            ('token.test.js', 0, 'token expired', 'AssertionError: assert stale'),
        ],
        "absent_names": ["stale"],
        "rerun": "npx vitest run token.test.js -t 'token expired'",
    },
    {
        "id": "vitest-printed-report-before-banner",
        "dialect": "vitest",
        "argv": ["npx", "vitest", "run", "token.test.js"],
        "log": """
⎯⎯⎯⎯⎯⎯⎯ Failed Tests 1 ⎯⎯⎯⎯⎯⎯⎯

 FAIL  old.test.js > stale
AssertionError: stale
 ❯ old.test.js:3:1

⎯⎯⎯⎯⎯⎯⎯ Failed Tests 1 ⎯⎯⎯⎯⎯⎯⎯

 FAIL  token.test.js > token expired
AssertionError: assert stale
 ❯ token.test.js:47:4
 Test Files  1 failed
""",
                "expect": [
            ('token.test.js', 0, 'token expired', 'AssertionError: assert stale'),
        ],
        "absent_files": ["old.test.js"],
        "rerun": "npx vitest run token.test.js -t 'token expired'",
    },
    {
        "id": "cargo-printed-panic",
        "dialect": "cargo",
        "argv": ["cargo", "test", "--offline", "--", "--test-threads=1"],
        "log": """
thread 'old::stale' panicked at old.rs:1:1:
old boom
thread 'auth::token_expired' panicked at src/lib.rs:10:1:
first boom
thread 'auth::token_expired' panicked at src/lib.rs:40:1:
live boom

failures:
    auth::token_expired

test result: FAILED
""",
                "expect": [
            ('', 0, 'auth::token_expired', ''),
        ],
        "absent_names": ["old::stale"],
        "rerun": 'cargo test --offline auth::token_expired -- --exact',
    },
    {
        "id": "cargo-printed-report-before-live",
        "dialect": "cargo",
        "argv": ["cargo", "test", "--offline", "--", "--test-threads=1"],
        "log": """
thread 'old::stale' panicked at old.rs:1:1:
old boom

failures:
    old::stale

test result: FAILED

thread 'auth::token_expired' panicked at src/lib.rs:10:1:
live boom

failures:
    auth::token_expired

test result: FAILED
""",
                "expect": [
            ('', 0, 'auth::token_expired', ''),
        ],
        "absent_names": ["old::stale"],
        "rerun": 'cargo test --offline auth::token_expired -- --exact',
    },
    {
        "id": "go-indented-printed-log",
        "dialect": "go",
        "argv": ["go", "test", "-count=1", "."],
        "log": """
--- FAIL: TestOne (0.00s)
    --- FAIL: TestOld (0.00s)
        old_test.go:1: old
    a_test.go:3: one mismatch
FAIL
FAIL	example.com/tokenbox	0.01s
""",
                "expect": [
            ('', 0, 'TestOne', ''),
        ],
        "absent_names": ["TestOld"],
        "rerun": "go test -count=1 -run '^TestOne$' .",
    },
    {
        "id": "go-printed-package-before-live",
        "dialect": "go",
        "argv": ["go", "test", "-count=1", "."],
        "log": """
--- FAIL: TestOld (0.00s)
    old_test.go:1: old
FAIL
FAIL	example.com/old	0.01s
--- FAIL: TestOne (0.00s)
    a_test.go:3: one mismatch
FAIL
FAIL	example.com/tokenbox	0.01s
""",
                "expect": [
            ('', 0, 'TestOne', ''),
        ],
        "absent_names": ["TestOld"],
        "rerun": "go test -count=1 -run '^TestOne$' .",
    },
    {
        "id": "eslint-dotdot-omits-rerun",
        "dialect": "eslint",
        "argv": ["npx", "eslint", "lint-me.js"],
        "log": """
../../lint-me.js
  1:1  error  first message here                 no-unused-vars
1 problem
""",
                "expect": [
            ('../../lint-me.js', 1, 'no-unused-vars', 'first message here'),
        ],
        "rerun": None,
        "block_rerun": True,
    },
    {
        "id": "pytest-tb-line-printed-session",
        "dialect": "pytest",
        "argv": ["python", "-m", "pytest", "-q", "--tb=line", "test_same.py"],
        "log": """
=================================== FAILURES ===================================
E   assert 1 == 2
----------------------------- Captured stdout call -----------------------------
=================================== FAILURES ===================================
______________________________ test_token_expired ______________________________
E       AssertionError: stale
tests/test_auth.py:167: AssertionError
=========================== short test summary info ============================
FAILED tests/test_auth.py::test_token_expired - AssertionError: stale
============================== 1 failed in 0.01s ===============================
/tmp/test_same.py:4: assert 1 == 2
=========================== short test summary info ============================
FAILED test_same.py::test_token_expired - assert 1 == 2
============================== 1 failed in 0.02s ===============================
""",
                "expect": [
            ('test_same.py', 0, 'test_token_expired', 'assert 1 == 2'),
        ],
        "absent_files": ["tests/test_auth.py"],
        "rerun": 'python -m pytest test_same.py -k test_token_expired',
    },
    {
        "id": "pytest-tb-no-printed-session",
        "dialect": "pytest",
        "argv": ["python", "-m", "pytest", "-q", "--tb=no", "test_same.py"],
        "log": """
=================================== FAILURES ===================================
______________________________ test_token_expired ______________________________
E       AssertionError: stale
tests/test_auth.py:167: AssertionError
=========================== short test summary info ============================
FAILED tests/test_auth.py::test_token_expired - AssertionError: stale
============================== 1 failed in 0.01s ===============================
=========================== short test summary info ============================
FAILED test_same.py::test_token_expired - assert 1 == 2
============================== 1 failed in 0.02s ===============================
""",
                "expect": [
            ('test_same.py', 0, 'test_token_expired', 'assert 1 == 2'),
        ],
        "absent_files": ["tests/test_auth.py"],
        "rerun": 'python -m pytest test_same.py -k test_token_expired',
    },
    {
        "id": "pytest-tb-short-reprint",
        "dialect": "pytest",
        "argv": ["python", "-m", "pytest", "-q", "--tb=short", "test_same.py"],
        "log": """
=================================== FAILURES ===================================
______________________________ test_token_expired ______________________________
test_same.py:4: in test_token_expired
    assert 1 == 2
E   assert 1 == 2
----------------------------- Captured stdout call -----------------------------
______________________________ test_token_expired ______________________________
E       assert 1 == 2
test_same.py:167: AssertionError
=========================== short test summary info ============================
FAILED test_same.py::test_token_expired - assert 1 == 2
============================== 1 failed in 0.02s ===============================
""",
                "expect": [
            ('test_same.py', 0, 'test_token_expired', 'assert 1 == 2'),
        ],
        "rerun": 'python -m pytest test_same.py -k test_token_expired',
    },
    {
        "id": "pytest-tb-line-reprint",
        "dialect": "pytest",
        "argv": ["python", "-m", "pytest", "-q", "--tb=line", "test_same.py"],
        "log": """
=================================== FAILURES ===================================
E   assert 1 == 2
----------------------------- Captured stdout call -----------------------------
______________________________ test_token_expired ______________________________
E       assert 1 == 2
test_same.py:167: AssertionError
test_same.py:4: assert 1 == 2
=========================== short test summary info ============================
FAILED test_same.py::test_token_expired - assert 1 == 2
============================== 1 failed in 0.02s ===============================
""",
                "expect": [
            ('test_same.py', 0, 'test_token_expired', 'assert 1 == 2'),
        ],
        "rerun": 'python -m pytest test_same.py -k test_token_expired',
    },
    {
        "id": "pytest-node-space-and-dash",
        "dialect": "pytest",
        "argv": PYTEST_ARGV,
        "log": """
=================================== FAILURES ===================================
_________________________ test_person[hello world] _____________________________
E       AssertionError: assert 'hello world' == 'present'
test_names.py:6: AssertionError
____________________________ test_person[a - b] ________________________________
E       AssertionError: assert 'a - b' == 'present'
test_names.py:6: AssertionError
__________________________ test_person[say "hi"] _______________________________
E       AssertionError: assert 'say "hi"' == 'present'
test_names.py:6: AssertionError
__________________________ test_person[Jos\\xe9] _______________________________
E       AssertionError: assert 'José' == 'present'
test_names.py:6: AssertionError
=========================== short test summary info ============================
FAILED test_names.py::test_person[hello world] - AssertionError: assert 'hello world' == 'present'
FAILED test_names.py::test_person[a - b] - AssertionError: assert 'a - b' == 'present'
FAILED test_names.py::test_person[say "hi"] - AssertionError: assert 'say "hi"' == 'present'
FAILED test_names.py::test_person[Jos\\xe9] - AssertionError: assert 'José' == 'present'
============================== 4 failed in 0.02s ===============================
""",
                "expect": [
            ('test_names.py', 0, 'test_person[hello world]', "AssertionError: assert 'hello world' == 'present'"),
            ('test_names.py', 0, 'test_person[a - b]', "AssertionError: assert 'a - b' == 'present'"),
            ('test_names.py', 0, 'test_person[say "hi"]', 'AssertionError: assert \'say "hi"\' == \'present\''),
            ('test_names.py', 0, 'test_person[Jos\\xe9]', "AssertionError: assert 'José' == 'present'"),
        ],
        "rerun": None,
    },
    {
        "id": "pytest-tb-native",
        "dialect": "pytest",
        "argv": ["python", "-m", "pytest", "-q", "--tb=native", "test_plain.py"],
        "log": """
=================================== FAILURES ===================================
__________________________________ test_plain __________________________________
Traceback (most recent call last):
  File "/usr/lib/pytest/runner.py", line 10, in run
    item.runtest()
  File "/tmp/test_plain.py", line 2, in test_plain
    assert 1 == 2
AssertionError: assert 1 == 2
=========================== short test summary info ============================
FAILED test_plain.py::test_plain - assert 1 == 2
============================== 1 failed in 0.01s ===============================
""",
                "expect": [
            ('test_plain.py', 0, 'test_plain', 'assert 1 == 2'),
        ],
        "rerun": 'python -m pytest test_plain.py -k test_plain',
    },
    {
        "id": "pytest-tail-sliced-banner",
        "dialect": "pytest",
        "argv": ["python", "-m", "pytest", "-q", "test_token.py"],
        "log": """
==============================
______________________________ test_token_expired ______________________________

    def test_token_expired():
>       assert 1 == 0
E       assert 1 == 0

test_token.py:3: AssertionError
----------------------------- Captured stdout call -----------------------------
stale token line 000
=========================== short test summary info ============================
FAILED test_token.py::test_token_expired - assert 1 == 0
============================== 1 failed in 0.01s ===============================
""",
                "expect": [
            ('test_token.py', 0, 'test_token_expired', 'assert 1 == 0'),
        ],
        "rerun": 'python -m pytest test_token.py -k test_token_expired',
    },
    {
        "id": "pytest-tail-deep-cut",
        "dialect": "pytest",
        "argv": ["python", "-m", "pytest", "-q", "--tb=long", "test_token.py"],
        "log": """
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

    def dive(n):
>       assert 1 == 0
E       assert 1 == 0

test_token.py:4: AssertionError
=========================== short test summary info ============================
FAILED test_token.py::test_token_expired - assert 1 == 0
============================== 1 failed in 0.01s ===============================
""",
                "expect": [
            ('test_token.py', 0, 'test_token_expired', 'assert 1 == 0'),
        ],
        "rerun": 'python -m pytest test_token.py -k test_token_expired',
    },
    {
        "id": "pytest-tail-tb-line-absolute",
        "dialect": "pytest",
        "argv": ["python", "-m", "pytest", "-q", "--tb=line", "test_same.py"],
        "log": """
  - fresh token line
/tmp/work/test_same.py:4: assert 1 == 2
=========================== short test summary info ============================
FAILED test_same.py::test_token_expired - assert 1 == 2
============================== 1 failed in 0.02s ===============================
""",
                "expect": [
            ('test_same.py', 0, 'test_token_expired', 'assert 1 == 2'),
        ],
        "absent_files": ["tests/test_auth.py"],
        "rerun": 'python -m pytest test_same.py -k test_token_expired',
    },
    {
        "id": "pytest-tail-printed-section",
        "dialect": "pytest",
        "argv": ["python", "-m", "pytest", "-q", "-s", "--tb=no", "test_same.py"],
        "log": """
______________________________ test_token_expired ______________________________
E       assert 1 == 2
test_same.py:167: AssertionError
=========================== short test summary info ============================
FAILED test_same.py::test_token_expired - assert 1 == 2
============================== 1 failed in 0.02s ===============================
""",
                "expect": [
            ('test_same.py', 0, 'test_token_expired', 'assert 1 == 2'),
        ],
        "rerun": 'python -m pytest test_same.py -k test_token_expired',
    },
    {
        "id": "pytest-tail-relative-agreeing-print",
        "dialect": "pytest",
        "argv": ["python", "-m", "pytest", "-q", "-s", "--tb=no", "test_same.py"],
        "log": """
test_same.py:167: assert 1 == 2
F
=========================== short test summary info ============================
FAILED test_same.py::test_token_expired - assert 1 == 2
============================== 1 failed in 0.00s ===============================
""",
                "expect": [
            ('test_same.py', 0, 'test_token_expired', 'assert 1 == 2'),
        ],
        "rerun": 'python -m pytest test_same.py -k test_token_expired',
    },
    {
        "id": "pytest-tail-planted-exception",
        "dialect": "pytest",
        "argv": ["python", "-m", "pytest", "-q", "test_token.py"],
        "log": """
test_token.py:167: AssertionError
=========================== short test summary info ============================
FAILED test_token.py::test_token_expired - assert 1 == 0
============================== 1 failed in 0.01s ===============================
""",
                "expect": [
            ('test_token.py', 0, 'test_token_expired', 'assert 1 == 0'),
        ],
        "rerun": 'python -m pytest test_token.py -k test_token_expired',
    },
    {
        "id": "pytest-tail-capture-section",
        "dialect": "pytest",
        "argv": ["python", "-m", "pytest", "-q", "test_token.py"],
        "log": """
noise 0088 xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
noise 0089 xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
========================================
______________________________ test_token_expired ______________________________
E       assert 1 == 0
/tmp/old/test_token.py:999: AssertionError
=========================== short test summary info ============================
FAILED test_token.py::test_token_expired - assert 1 == 0
============================== 1 failed in 0.01s ===============================
""",
                "expect": [
            ('test_token.py', 0, 'test_token_expired', 'assert 1 == 0'),
        ],
        "absent_files": ["/tmp/old/test_token.py"],
        "rerun": 'python -m pytest test_token.py -k test_token_expired',
    },
    {
        "id": "pytest-tail-printed-abs-line",
        "dialect": "pytest",
        "argv": ["python", "-m", "pytest", "-q", "test_token.py"],
        "log": """
noise 0088 xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
noise 0089 xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
/tmp/old/test_token.py:999: assert 1 == 0
=========================== short test summary info ============================
FAILED test_token.py::test_token_expired - assert 1 == 0
============================== 1 failed in 0.01s ===============================
""",
                "expect": [
            ('test_token.py', 0, 'test_token_expired', 'assert 1 == 0'),
        ],
        "absent_files": ["/tmp/old/test_token.py"],
        "rerun": 'python -m pytest test_token.py -k test_token_expired',
    },
    {
        "id": "pytest-tail-plain-stdout",
        "dialect": "pytest",
        "argv": ["python", "-m", "pytest", "-q", "test_token.py"],
        "log": """
row 0198
row 0199
=========================== short test summary info ============================
FAILED test_token.py::test_token_expired - assert 1 == 0
============================== 1 failed in 0.01s ===============================
""",
                "expect": [
            ('test_token.py', 0, 'test_token_expired', 'assert 1 == 0'),
        ],
        "rerun": 'python -m pytest test_token.py -k test_token_expired',
    },
    {
        "id": "pytest-tail-tb-line-after-footer",
        "dialect": "pytest",
        "argv": ["python", "-m", "pytest", "-q", "test_same.py"],
        "log": """
  + stale token line
========================= 1 failed, 40 passed in 0.07s =========================

/tmp/work/test_same.py:4: assert 1 == 2
=========================== short test summary info ============================
FAILED test_same.py::test_token_expired - assert 1 == 2
============================== 1 failed in 0.02s ===============================
""",
                "expect": [
            ('test_same.py', 0, 'test_token_expired', 'assert 1 == 2'),
        ],
        "absent_files": ["tests/test_auth.py", "/tmp/work/test_same.py"],
        "rerun": 'python -m pytest test_same.py -k test_token_expired',
    },
    {
        "id": "pytest-two-files",
        "dialect": "pytest",
        "argv": ["python", "-m", "pytest", "-q", "test_a.py", "test_b.py"],
        "log": """
=================================== FAILURES ===================================
___________________________________ test_a ____________________________________
E       assert 0 == -1
test_a.py:3: AssertionError
___________________________________ test_b ____________________________________
E       assert 1 == -1
test_b.py:3: AssertionError
=========================== short test summary info ============================
FAILED test_a.py::test_a - assert 0 == -1
FAILED test_b.py::test_b - assert 1 == -1
============================== 2 failed in 0.01s ===============================
""",
                "expect": [
            ('test_a.py', 0, 'test_a', 'assert 0 == -1'),
            ('test_b.py', 0, 'test_b', 'assert 1 == -1'),
        ],
        "rerun": "python -m pytest test_a.py test_b.py -k 'test_a or test_b'",
    },
    {
        "id": "jest-path-with-space",
        "dialect": "jest",
        "argv": ["npx", "jest", "my tests/auth.test.js"],
        "log": """
FAIL my tests/auth.test.js
  ● token expired
      > 47 | expect(a).toBe(b);
      at Object.toBe (my tests/auth.test.js:47:1)
Test Suites: 1 failed, 1 total
""",
                "expect": [
            ('my tests/auth.test.js', 0, 'token expired', ''),
        ],
        "rerun": "npx jest 'my tests/auth.test.js' -t 'token expired'",
    },
    {
        "id": "vitest-path-with-space",
        "dialect": "vitest",
        "argv": ["npx", "vitest", "run", "my tests/token.test.js"],
        "log": """
⎯⎯⎯⎯⎯⎯⎯ Failed Tests 1 ⎯⎯⎯⎯⎯⎯⎯

 FAIL  my tests/token.test.js > token expired
AssertionError: assert stale
 ❯ my tests/token.test.js:47:4
 Test Files  1 failed
""",
                "expect": [
            ('my tests/token.test.js', 0, 'token expired', 'AssertionError: assert stale'),
        ],
        "rerun": "npx vitest run 'my tests/token.test.js' -t 'token expired'",
    },
    {
        "id": "go-path-with-space",
        "dialect": "go",
        "argv": ["go", "test", "-count=1", "."],
        "log": """
--- FAIL: TestOne (0.00s)
    my file_test.go:3: one mismatch
FAIL
FAIL	example.com/tokenbox	0.01s
""",
                "expect": [
            ('', 0, 'TestOne', ''),
        ],
        "rerun": "go test -count=1 -run '^TestOne$' .",
    },
    {
        "id": "ruff-path-with-space",
        "dialect": "ruff",
        "argv": ["ruff", "check", "my file.py"],
        "log": """
F401 unused import
  --> my file.py:1:8
Found 1 error
""",
                "expect": [
            ('my file.py', 1, 'F401', 'unused import'),
        ],
        "rerun": "ruff check 'my file.py'",
    },
    {
        "id": "cargo-path-with-space",
        "dialect": "cargo",
        "argv": ["cargo", "test", "--offline", "--", "--test-threads=1"],
        "log": """
thread 'auth::token_expired' panicked at my file.rs:10:1:
live boom

failures:
    auth::token_expired

test result: FAILED
""",
                "expect": [
            ('', 0, 'auth::token_expired', ''),
        ],
        "rerun": 'cargo test --offline auth::token_expired -- --exact',
    },
    {
        "id": "jest-tail-no-fail-word",
        "dialect": None,
        "argv": ["npx", "jest", "auth.test.js"],
        "log": """
    - fresh token line
      at Object.toBe (old.test.js:3:1)
      at Object.toBe (auth.test.js:47:15)

Test Suites: 1 failed, 1 total
Tests:       1 failed, 40 passed, 41 total
""",
                "expect": [
        ],
        "absent_files": ["old.test.js"],
        "rerun": None,
    },
    {
        "id": "vitest-tail-no-fail-head",
        "dialect": None,
        "argv": ["npx", "vitest", "run", "token.test.js"],
        "log": """
- fresh token line
 ❯ old.test.js:3:1
 ❯ token.test.js:47:15

 Test Files  1 failed (1)
      Tests  1 failed | 40 passed (41)
""",
                "expect": [
        ],
        "absent_files": ["old.test.js"],
        "rerun": None,
    },
    {
        "id": "eslint-tail-no-file-header",
        "dialect": "eslint",
        "argv": ["npx", "eslint", "lint-me.js"],
        "log": """
  56:7  error  'unused_55' is assigned a value but never used  no-unused-vars
  57:7  error  'unused_56' is assigned a value but never used  no-unused-vars

✖ 80 problems (80 errors, 0 warnings)
""",
                "expect": [
            ('', 56, 'no-unused-vars', "'unused_55' is assigned a value but never used"),
            ('', 57, 'no-unused-vars', "'unused_56' is assigned a value but never used"),
        ],
        "rerun": None,
    },
    {
        "id": "pytest-width-dropped",
        "dialect": "pytest",
        "argv": ["python", "-m", "pytest", "-q", "/var/folders/longpath/work/test_token.py"],
        "log": """
=================================== FAILURES ===================================
______________________________ test_token_expired ______________________________

    def test_token_expired():
>       assert 1 == 0
E       assert 1 == 0

/var/work/test_token.py:3: AssertionError
----------------------------- Captured stdout call -----------------------------
E       assert 9 == 8
=========================== short test summary info ============================
FAILED ../../../../../../../../var/folders/longpath/work/test_token.py::test_token_expired
============================== 1 failed in 0.02s ===============================
""",
        "expect": [
            ("../../../../../../../../var/folders/longpath/work/test_token.py", 0, "test_token_expired", "assert 1 == 0"),
        ],
        "anchor_prefix": "E       assert 1 == 0",
        "absent_points": ["assert 9 == 8"],
        "rerun": None,
    },
    {
        "id": "pytest-width-ellipsis",
        "dialect": "pytest",
        "argv": ["python", "-m", "pytest", "-q", "test_t.py"],
        "log": """
=================================== FAILURES ===================================
________________________ test_token_expired[a - b] _________________________
>       assert name == 'no'
E       AssertionError: assert 'a - b' == 'no'
E         
E         - no
E         + a - b
test_t.py:4: AssertionError
=========================== short test summary info ============================
FAILED test_t.py::test_token_expired[a - b] - AssertionError: assert 'a - b' ...
1 failed in 0.02s
""",
        "expect": [
            ("test_t.py", 0, "test_token_expired[a - b]", "AssertionError: assert 'a - b' == 'no'"),
        ],
        "anchor_prefix": "E       AssertionError: assert 'a - b' == 'no'",
        "rerun": None,
    },
    {
        "id": "pytest-width-short-empty",
        "dialect": "pytest",
        "argv": ["python", "-m", "pytest", "-q", "test_t.py"],
        "log": """
=================================== FAILURES ===================================
__________________________________ test_one ___________________________________
E       RuntimeError: boom
test_t.py:4: RuntimeError
=========================== short test summary info ============================
FAILED test_t.py::test_one
1 failed in 0.01s
""",
        "expect": [
            ("test_t.py", 0, "test_one", ""),
        ],
        "anchor_prefix": "FAILED test_t.py::test_one",
        "rerun": "python -m pytest test_t.py -k test_one",
    },
    {
        "id": "pytest-width-keep-summary",
        "dialect": "pytest",
        "argv": ["python", "-m", "pytest", "-q", "test_t.py"],
        "log": """
=================================== FAILURES ===================================
______________________________ test_token_expired ______________________________
>       assert 1 == 0
E       assert 1 == 0
test_t.py:2: AssertionError
=========================== short test summary info ============================
FAILED test_t.py::test_token_expired - assert 1 == 0
1 failed in 0.02s
""",
        "expect": [
            ("test_t.py", 0, "test_token_expired", "assert 1 == 0"),
        ],
        "anchor_prefix": "FAILED test_t.py::test_token_expired - assert 1 == 0",
        "rerun": "python -m pytest test_t.py -k test_token_expired",
    },
    {
        "id": "pytest-width-class",
        "dialect": "pytest",
        "argv": ["python", "-m", "pytest", "-q", "/var/folders/longpath/work/test_t.py"],
        "log": """
=================================== FAILURES ===================================
__________________________ TestBox.test_token_expired __________________________
    def test_token_expired(self):
>       assert 1 == 0
E       assert 1 == 0
test_t.py:3: AssertionError
=========================== short test summary info ============================
FAILED ../../../../../../../../var/folders/longpath/work/test_t.py::TestBox::test_token_expired
1 failed in 0.02s
""",
        "expect": [
            ("../../../../../../../../var/folders/longpath/work/test_t.py", 0, "test_token_expired", "assert 1 == 0"),
        ],
        "anchor_prefix": "E       assert 1 == 0",
        "rerun": None,
    },
    {
        "id": "pytest-width-two",
        "dialect": "pytest",
        "argv": ["python", "-m", "pytest", "-q", "/var/folders/longpath/work/test_token.py"],
        "log": """
=================================== FAILURES ===================================
__________________________________ test_one ___________________________________
>       assert 1 == 0
E       assert 1 == 0
/var/folders/longpath/work/test_token.py:3: AssertionError
__________________________________ test_two ___________________________________
>       assert 'left' == 'right'
E       AssertionError: assert 'left' == 'right'
/var/folders/longpath/work/test_token.py:6: AssertionError
=========================== short test summary info ============================
FAILED ../../../../../../../../var/folders/longpath/work/test_token.py::test_one
FAILED ../../../../../../../../var/folders/longpath/work/test_token.py::test_two
2 failed in 0.02s
""",
        "expect": [
            ("../../../../../../../../var/folders/longpath/work/test_token.py", 0, "test_one", "assert 1 == 0"),
            ("../../../../../../../../var/folders/longpath/work/test_token.py", 0, "test_two", "AssertionError: assert 'left' == 'right'"),
        ],
        "anchor_prefix": "E       assert 1 == 0",
        "rerun": None,
    },
    {
        "id": "pytest-width-tb-line",
        "dialect": "pytest",
        "argv": ["python", "-m", "pytest", "-q", "--tb=line", "/var/folders/longpath/work/test_token.py"],
        "log": """
=================================== FAILURES ===================================
E   assert 1 == 0
----------------------------- Captured stdout call -----------------------------
E       assert 9 == 8
/var/folders/longpath/work/test_token.py:3: assert 1 == 0
=========================== short test summary info ============================
FAILED ../../../../../../../../var/folders/longpath/work/test_token.py::test_token_expired
1 failed in 0.00s
""",
        "expect": [
            ("../../../../../../../../var/folders/longpath/work/test_token.py", 0, "test_token_expired", "assert 1 == 0"),
        ],
        "anchor_prefix": "E   assert 1 == 0",
        "absent_points": ["assert 9 == 8"],
        "rerun": None,
    },
    {
        "id": "pytest-width-tb-line-two",
        "dialect": "pytest",
        "argv": ["python", "-m", "pytest", "-q", "--tb=line", "/var/folders/longpath/work/test_token.py"],
        "log": """
=================================== FAILURES ===================================
E   assert 1 == 0
----------------------------- Captured stdout call -----------------------------
pad
/var/folders/longpath/work/test_token.py:3: assert 1 == 0
E   AssertionError: assert 'left' == 'right'
/var/folders/longpath/work/test_token.py:6: AssertionError: assert 'left' == 'right'
=========================== short test summary info ============================
FAILED ../../../../../../../../var/folders/longpath/work/test_token.py::test_one
FAILED ../../../../../../../../var/folders/longpath/work/test_token.py::test_two
2 failed in 0.00s
""",
        "expect": [
            ("../../../../../../../../var/folders/longpath/work/test_token.py", 0, "test_one", "assert 1 == 0"),
            ("../../../../../../../../var/folders/longpath/work/test_token.py", 0, "test_two", "AssertionError: assert 'left' == 'right'"),
        ],
        "anchor_prefix": "E   assert 1 == 0",
        "rerun": None,
    },
    {
        "id": "pytest-width-printed-heading",
        "dialect": "pytest",
        "argv": ["python", "-m", "pytest", "-s", "-q", "/var/folders/longpath/work/test_token.py"],
        "log": """
=================================== FAILURES ===================================
______________________________ test_token_expired ______________________________
E       assert 9 == 8
/tmp/old/test_token.py:167: AssertionError
=========================== short test summary info ============================
FAILED /tmp/old/test_token.py::test_token_expired - assert 9 == 8
============================== 1 failed in 0.01s ===============================
=================================== FAILURES ===================================
______________________________ test_token_expired ______________________________
>       assert 1 == 0
E       assert 1 == 0
/var/folders/longpath/work/test_token.py:3: AssertionError
=========================== short test summary info ============================
FAILED ../../../../../../../../var/folders/longpath/work/test_token.py::test_token_expired
============================== 1 failed in 0.02s ===============================
""",
        "expect": [
            ("../../../../../../../../var/folders/longpath/work/test_token.py", 0, "test_token_expired", "assert 1 == 0"),
        ],
        "anchor_prefix": "E       assert 1 == 0",
        "absent_files": ["/tmp/old/test_token.py"],
        "absent_points": ["assert 9 == 8"],
        "rerun": None,
    },
    {
        "id": "pytest-width-chain",
        "dialect": "pytest",
        "argv": ["python", "-m", "pytest", "-q", "/var/folders/longpath/work/test_token.py"],
        "log": """
=================================== FAILURES ===================================
______________________________ test_token_expired ______________________________
E       ValueError: inner
The above exception was the direct cause of the following exception:
E       RuntimeError: outer
/var/folders/longpath/work/test_token.py:4: RuntimeError
=========================== short test summary info ============================
FAILED ../../../../../../../../var/folders/longpath/work/test_token.py::test_token_expired
1 failed in 0.02s
""",
        "expect": [
            ("../../../../../../../../var/folders/longpath/work/test_token.py", 0, "test_token_expired", "RuntimeError: outer"),
        ],
        "anchor_prefix": "E       RuntimeError: outer",
        "absent_points": ["ValueError: inner"],
        "rerun": None,
    },
    {
        "id": "pytest-width-syntax",
        "dialect": "pytest",
        "argv": ["python", "-m", "pytest", "-q", "/var/folders/longpath/work/test_syn.py"],
        "log": """
==================================== ERRORS ====================================
_________________________ ERROR collecting test_syn.py _________________________
E     File "/var/folders/longpath/work/test_syn.py", line 1
E       def (
E           ^
E   SyntaxError: invalid syntax
=========================== short test summary info ============================
ERROR ../../../../../../../../../../../var/folders/longpath/work/test_syn.py
1 error in 0.04s
""",
        "expect": [
            ("../../../../../../../../../../../var/folders/longpath/work/test_syn.py", 0, "", "SyntaxError: invalid syntax"),
        ],
        "anchor_prefix": "E   SyntaxError: invalid syntax",
        "rerun": None,
    },
    {
        "id": "pytest-width-collect-short",
        "dialect": "pytest",
        "argv": ["python", "-m", "pytest", "-q", "test_imp.py"],
        "log": """
==================================== ERRORS ====================================
_________________________ ERROR collecting test_imp.py _________________________
E   ModuleNotFoundError: No module named 'no_such_mod_zz'
=========================== short test summary info ============================
ERROR test_imp.py
1 error in 0.04s
""",
        "expect": [
            ("test_imp.py", 0, "", ""),
        ],
        "anchor_prefix": "ERROR test_imp.py",
        "rerun": None,
    },
    {
        "id": "pytest-width-boundary-74",
        "dialect": "pytest",
        "argv": ["python", "-m", "pytest", "-q", "t.py"],
        "log": """
=================================== FAILURES ===================================
__________________________________ test_one ___________________________________
E       assert 1 == 0
t.py:2: AssertionError
=========================== short test summary info ============================
FAILED ../../../../../../../../../../../../../../../../../d/t.py::test_one
1 failed in 0.01s
""",
        "expect": [
            ("../../../../../../../../../../../../../../../../../d/t.py", 0, "test_one", ""),
        ],
        "anchor_prefix": "FAILED ../../../../../../../../../../../../../../../../../d/t.py::test_one",
        "summary_cols": 74,
        "rerun": None,
    },
    {
        "id": "pytest-width-boundary-75",
        "dialect": "pytest",
        "argv": ["python", "-m", "pytest", "-q", "tt.py"],
        "log": """
=================================== FAILURES ===================================
__________________________________ test_one ___________________________________
E       assert 1 == 0
tt.py:2: AssertionError
=========================== short test summary info ============================
FAILED ../../../../../../../../../../../../../../../../../../t.py::test_one
1 failed in 0.01s
""",
        "expect": [
            ("../../../../../../../../../../../../../../../../../../t.py", 0, "test_one", "assert 1 == 0"),
        ],
        "anchor_prefix": "E       assert 1 == 0",
        "summary_cols": 75,
        "rerun": None,
    },
    {
        "id": "pytest-width-ellipsis-mismatch",
        "dialect": "pytest",
        "argv": ["python", "-m", "pytest", "-q", "test_t.py"],
        "log": """
=================================== FAILURES ===================================
__________________________________ test_one ___________________________________
E       RuntimeError: other
test_t.py:2: RuntimeError
=========================== short test summary info ============================
FAILED test_t.py::test_one - assert 1 == 0...
1 failed in 0.01s
""",
        "expect": [
            ("test_t.py", 0, "test_one", "assert 1 == 0..."),
        ],
        "anchor_prefix": "FAILED test_t.py::test_one - assert 1 == 0...",
        "rerun": "python -m pytest test_t.py -k test_one",
    },
    {
        "id": "pytest-width-natural-dots",
        "dialect": "pytest",
        "argv": ["python", "-m", "pytest", "-q", "test_t.py"],
        "log": """
=================================== FAILURES ===================================
______________________________ test_token_expired ______________________________
E       assert 'ab...cd' == 'no'
test_t.py:2: AssertionError
=========================== short test summary info ============================
FAILED test_t.py::test_token_expired - assert 'ab...cd' == 'no'
1 failed in 0.01s
""",
        "expect": [
            ("test_t.py", 0, "test_token_expired", "assert 'ab...cd' == 'no'"),
        ],
        "anchor_prefix": "FAILED test_t.py::test_token_expired - assert 'ab...cd' == 'no'",
        "rerun": "python -m pytest test_t.py -k test_token_expired",
    },
    {
        "id": "pytest-width-tail-no-banner",
        "dialect": "pytest",
        "argv": ["python", "-m", "pytest", "-q", "/var/folders/longpath/work/test_token.py"],
        "log": """
E       assert 1 == 0
/var/work/test_token.py:3: AssertionError
=========================== short test summary info ============================
FAILED ../../../../../../../../var/folders/longpath/work/test_token.py::test_token_expired
1 failed in 0.02s
""",
        "expect": [
            ("../../../../../../../../var/folders/longpath/work/test_token.py", 0, "test_token_expired", ""),
        ],
        "anchor_prefix": "FAILED ../../../../../../../../var/folders/longpath/work/test_token.py::test_token_expired",
        "rerun": None,
    },
    {
        "id": "pytest-width-setup",
        "dialect": "pytest",
        "argv": ["python", "-m", "pytest", "-q", "/var/folders/longpath/work/test_t.py"],
        "log": """
==================================== ERRORS ====================================
_________________________ ERROR at setup of test_needs _________________________
E       RuntimeError: fixture broke
test_t.py:4: RuntimeError
=========================== short test summary info ============================
ERROR ../../../../../../../../var/folders/longpath/work/test_t.py::test_needs
1 error in 0.02s
""",
        "expect": [
            ("../../../../../../../../var/folders/longpath/work/test_t.py", 0, "test_needs", "RuntimeError: fixture broke"),
        ],
        "anchor_prefix": "E       RuntimeError: fixture broke",
        "rerun": None,
    },
]

LIVE_ROWS = (
    "pytest-real-captured-stale",
    "pytest-real-helper",
    "pytest-real-dotdot",
    "pytest-real-dashs",
)

# Real pytest 9.1.1 rows. The cite is the node id on the summary line.
# The line number on that cite is 0. A printed path, a helper frame, and a
# --tb value do not change the cite. `line`, `full_line`, and `file_suffix`
# record an older traceback guess. The test does not cite them.
CRASH_LINE_ROWS = (
    {"id": "ini-long", "config": "ini", "shape": "long", "args": ["-q", "test_token.py"], "command": "python -m pytest -q test_token.py", "line": 3},
    {"id": "pyproject-long", "config": "pyproject", "shape": "long", "args": ["-q", "test_token.py"], "command": "python -m pytest -q test_token.py", "line": 3},
    {"id": "setupcfg-long", "config": "setupcfg", "shape": "long", "args": ["-q", "test_token.py"], "command": "python -m pytest -q test_token.py", "line": 3},
    {"id": "env-long", "config": "env", "shape": "long", "args": ["-q", "test_token.py"], "command": "python -m pytest -q test_token.py", "line": 3},
    {"id": "cmd-long", "config": "none", "shape": "long", "args": ["-q", "--tb=line", "test_token.py"], "command": "python -m pytest -q --tb=line test_token.py", "line": 3},
    {"id": "ini-short", "config": "ini", "shape": "short", "args": ["-q", "test_token.py"], "command": "python -m pytest -q test_token.py", "line": 2},
    {"id": "default-missing", "config": "none", "shape": "fake", "args": ["-q", "test_token.py"], "command": "python -m pytest -q test_token.py", "line": 0},
    {"id": "ini-after-fake", "config": "ini", "shape": "fake", "args": ["-q", "test_token.py"], "command": "python -m pytest -q test_token.py", "line": 4},
    {"id": "cmd-after-fake", "config": "none", "shape": "fake", "args": ["-q", "--tb=line", "test_token.py"], "command": "python -m pytest -q --tb=line test_token.py", "line": 4},
    {"id": "printed-banner", "config": "none", "shape": "banner", "args": ["-q", "test_token.py"], "command": "python -m pytest -q test_token.py", "line": 0, "full_line": 5},
    {"id": "printed-errors", "config": "none", "shape": "errors", "args": ["-q", "test_token.py"], "command": "python -m pytest -q test_token.py", "line": 0, "full_line": 5},
    {"id": "foreign-assert", "config": "none", "shape": "foreign-assert", "args": ["-q", "test_token.py"], "command": "python -m pytest -q test_token.py", "line": 0, "full_line": 4},
    {"id": "ini-foreign-assert", "config": "ini", "shape": "foreign-assert", "args": ["-q", "test_token.py"], "command": "python -m pytest -q test_token.py", "line": 4},
    {"id": "foreign-value", "config": "none", "shape": "foreign-value", "args": ["-q", "test_token.py"], "command": "python -m pytest -q test_token.py", "line": 0, "full_line": 4},
    {"id": "same-return", "config": "none", "shape": "same-return", "args": ["-q", "test_token.py"], "command": "python -m pytest -q test_token.py", "line": 0, "full_line": 6},
    {"id": "raise-helper", "config": "ini", "shape": "raise-helper", "args": ["-q", "test_token.py"], "command": "python -m pytest -q test_token.py", "line": 2, "file_suffix": "helper.py"},
    {"id": "footer-real", "config": "none", "shape": "footer", "args": ["-q", "test_token.py"], "command": "python -m pytest -q test_token.py", "line": 0},
    {"id": "printed-def", "config": "none", "shape": "def-line", "args": ["-q", "test_token.py"], "command": "python -m pytest -q test_token.py", "line": 0},
    {"id": "printed-other-assert", "config": "none", "shape": "other", "args": ["-q", "test_token.py"], "command": "python -m pytest -q test_token.py", "line": 0},
    {"id": "ini-after-other", "config": "ini", "shape": "other", "args": ["-q", "test_token.py"], "command": "python -m pytest -q test_token.py", "line": 5},
    {"id": "helper-ini", "config": "ini", "shape": "helper", "args": ["-q", "test_token.py"], "command": "python -m pytest -q test_token.py", "line": 2, "file_suffix": "helper.py"},
    {"id": "tb-no-real", "config": "none", "shape": "tb-no", "args": ["-q", "-s", "--tb=no", "test_token.py"], "command": "python -m pytest -q -s --tb=no test_token.py", "line": 0},
    {"id": "ini-raise-bare", "config": "ini", "shape": "raise-bare", "args": ["-q", "test_token.py"], "command": "python -m pytest -q test_token.py", "line": 3},
    {"id": "pyproject-raise-bare", "config": "pyproject", "shape": "raise-bare", "args": ["-q", "test_token.py"], "command": "python -m pytest -q test_token.py", "line": 3},
    {"id": "setupcfg-raise-bare", "config": "setupcfg", "shape": "raise-bare", "args": ["-q", "test_token.py"], "command": "python -m pytest -q test_token.py", "line": 3},
    {"id": "tox-raise-bare", "config": "tox", "shape": "raise-bare", "args": ["-q", "test_token.py"], "command": "python -m pytest -q test_token.py", "line": 3},
    {"id": "toml-raise-bare", "config": "toml", "shape": "raise-bare", "args": ["-q", "test_token.py"], "command": "python -m pytest -q test_token.py", "line": 3},
    {"id": "dotini-raise-bare", "config": "dotini", "shape": "raise-bare", "args": ["-q", "test_token.py"], "command": "python -m pytest -q test_token.py", "line": 3},
    {"id": "pyproject-list-raise", "config": "pyproject-list", "shape": "raise-bare", "args": ["-q", "test_token.py"], "command": "python -m pytest -q test_token.py", "line": 3},
    {"id": "env-raise-bare", "config": "env", "shape": "raise-bare", "args": ["-q", "test_token.py"], "command": "python -m pytest -q test_token.py", "line": 3},
    {"id": "cmd-raise-bare", "config": "none", "shape": "raise-bare", "args": ["-q", "--tb=line", "test_token.py"], "command": "python -m pytest -q --tb=line test_token.py", "line": 3},
    {"id": "ini-raise-msg", "config": "ini", "shape": "raise-msg", "args": ["-q", "test_token.py"], "command": "python -m pytest -q test_token.py", "line": 3},
    {"id": "parent-raise", "config": "ini", "shape": "raise-bare", "rel": "tests/test_token.py", "args": ["-q", "tests/test_token.py"], "command": "python -m pytest -q tests/test_token.py", "line": 3},
    {"id": "foreign-bare", "config": "none", "shape": "foreign-bare", "args": ["-q", "test_token.py"], "command": "python -m pytest -q test_token.py", "line": 0, "full_line": 4},
    {"id": "foreign-raise-live", "config": "none", "shape": "foreign-raise-live", "args": ["-q", "test_token.py"], "command": "python -m pytest -q test_token.py", "line": 0, "full_line": 4},
    {"id": "comment-bare", "config": "none", "shape": "comment-bare", "args": ["-q", "test_token.py"], "command": "python -m pytest -q test_token.py", "line": 0, "full_line": 5},
    {"id": "ini-raise-footer", "config": "ini", "shape": "raise-footer", "args": ["-q", "test_token.py"], "command": "python -m pytest -q test_token.py", "line": 4},
    {"id": "cmd-short-over-ini", "config": "ini", "shape": "raise-bare", "args": ["-q", "--tb=short", "test_token.py"], "command": "python -m pytest -q --tb=short test_token.py", "line": 0, "full_line": 3},
    {"id": "override-line", "config": "none", "shape": "raise-bare", "args": ["-q", "-o", "addopts=--tb=line", "test_token.py"], "command": "python -m pytest -q -o addopts=--tb=line test_token.py", "line": 3},
    {"id": "env-divzero", "config": "env", "shape": "divzero", "args": ["-q", "test_token.py"], "command": "python -m pytest -q test_token.py", "line": 3},
    {"id": "dotini-helper", "config": "dotini", "shape": "helper", "args": ["-q", "test_token.py"], "command": "python -m pytest -q test_token.py", "line": 2, "file_suffix": "helper.py"},
    {"id": "toml-helper", "config": "toml", "shape": "helper", "args": ["-q", "test_token.py"], "command": "python -m pytest -q test_token.py", "line": 2, "file_suffix": "helper.py"},
    {"id": "dottoml-helper", "config": "dottoml", "shape": "helper", "args": ["-q", "test_token.py"], "command": "python -m pytest -q test_token.py", "line": 2, "file_suffix": "helper.py"},
    {"id": "pyproject-helper", "config": "pyproject", "shape": "helper", "args": ["-q", "test_token.py"], "command": "python -m pytest -q test_token.py", "line": 2, "file_suffix": "helper.py"},
    {"id": "pyproject-list-helper", "config": "pyproject-list", "shape": "helper", "args": ["-q", "test_token.py"], "command": "python -m pytest -q test_token.py", "line": 2, "file_suffix": "helper.py"},
    {"id": "setupcfg-helper", "config": "setupcfg", "shape": "helper", "args": ["-q", "test_token.py"], "command": "python -m pytest -q test_token.py", "line": 2, "file_suffix": "helper.py"},
    {"id": "tox-helper", "config": "tox", "shape": "helper", "args": ["-q", "test_token.py"], "command": "python -m pytest -q test_token.py", "line": 2, "file_suffix": "helper.py"},
    {"id": "leading-env-helper", "config": "env", "shape": "helper", "args": ["-q", "test_token.py"], "command": "PYTEST_ADDOPTS=--tb=line python -m pytest -q test_token.py", "line": 2, "file_suffix": "helper.py"},
    {"id": "child-env-helper", "config": "env", "shape": "helper", "args": ["-q", "test_token.py"], "command": "python -m pytest -q test_token.py", "line": 0},
    {"id": "override-tb-no", "config": "none", "shape": "tb-no", "args": ["-q", "-s", "-o", "addopts=--tb=no", "test_token.py"], "command": "python -m pytest -q -s -o addopts=--tb=no test_token.py", "line": 0},
)


# Phrases that ask for the whole log. Inner whitespace, including U+3000, still matches.
PHRASE_ROWS = (
    ("\u5168\u90e8\u898b\u305b\u3066", True),
    ("\u5168\u90e8\u898b\u305b\u3066\u3002", True),
    ("\u3000\u5168\u90e8\u898b\u305b\u3066", True),
    ("\u5168\u90e8\u3000\u898b\u305b\u3066", True),
    ("show  me everything", True),
    ("SHOW ME EVERYTHING", True),
    ("show me everything;", True),
    ("\uff53\uff48\uff4f\uff57\u3000\uff4d\uff45\u3000\uff45\uff56\uff45\uff52\uff59\uff54\uff48\uff49\uff4e\uff47", True),
    ("\uff33\uff28\uff2f\uff37\u3000\uff2d\uff25\u3000\uff25\uff36\uff25\uff32\uff39\uff34\uff28\uff29\uff2e\uff27", True),
    ("\u5168\u6587\u3092\u898b\u305b\u3066", True),
    ("please show the full log now", True),
    ("<!-- \u5168\u90e8\u898b\u305b\u3066 --> run the tests", False),
    ("run the tests", False),
)
