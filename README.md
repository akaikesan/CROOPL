
## Environment
 Using venv is recommended.
```
$ python -m venv .venv 
$ source .venv/bin/activate
$ pip install -r requirements.txt
```


## Commands

You can run program by inputting the file to rooplppYacc.py.

```
python rooplppYacc.py <filename.rplpp>
```

If you got the error like this, 

```
.......
Too many open files .......
..............
```

resolve this error by running the commands below to change the limit of number of file descriptors.

```
$ ulimit -n 
256
$ ulimit -n 500
$ ulimit -n 
500
```

