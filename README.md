
## 実行環境
pythonの仮想環境venvを使っています。
```
$ python -m venv .venv 
$ source .venv/bin/activate
$ pip install -r requirements.txt
```


## 実行コマンド

rooplppYacc.py にCRooplppでファイル名を入力するとそのファイルが実行されます。
```
python rooplppYacc.py <filename.rplpp>
```

もしこのエラー
```
Too many open files
```
が出たら、Linux/macでは、ファイルディスクリプタ上限を設定し直すことでそれを解決できます。

```
$ ulimit -n 
256
$ ulimit -n 500
$ ulimit -n 
500
```

