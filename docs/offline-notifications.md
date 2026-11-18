# 通知先の切断とローカル作業

2026-11-19。ホスト側の修正。FW・app・通知形式は変更しない。

## 動作

本体の無線停止や切断でUDP socketが到達不能を通知しても、ローカルのコマンドを中止しない。
ホスト側に最新状態を保持し、既存の送信間隔で再送を試みる。
再送・再接続には従来どおり認証、5秒のpeer期限、別peerの新しいgenerationが必要。
切断エラーでpeerやgenerationを消去して、接続制限を緩める処理は追加しない。

対象はEHOSTUNREACH/ENETUNREACH/EHOSTDOWN/ENETDOWN/ECONNREFUSED。
socketの破損や権限など、これ以外のエラーは従来どおり停止する。
`device_connected`は認証HELLOを受けた履歴で、現在の無線状態や通知の到達確認ではない。

実機の終了前後にホストwatchがexit2となったことが調査のきっかけ。
その実行では具体的なerrnoを採取しておらず、同じ原因と確定したとは扱わない。
この修正は、到達不能を注入したホスト試験で実作業の継続を検証したもの。
本体の表示・物理キー・音の確認を代行した結果ではない。

## TDDと検証

```sh
uv run --locked python -m unittest discover -s tests -p test_offline_notifications.py
uv run --locked python -m unittest discover -s tests
uv run --locked python -m unittest discover -s tests/integration
```

先行3件のうち受信側のECONNREFUSEDでRed。送信側は最初のfixtureが250msの抑制内に収まり、失敗経路を通っていなかった。
送信時刻と最低1回の実送信をfixtureで保証してから、未修正コードの送受信2経路のRedを確認した。
最小実装後、仮想時計を進める前のUDP待機が0秒だったfixtureに競合が発生。
認証条件を維持し、datagramを有限待機で受け取ってから時計を進めるようにして成功した。

3件/0.193秒、標準54件/3.881秒、実SDK6件/2.402秒が成功、skipなし。
送信不可でも実プロセスがexit0へ到達すること、送信の間隔、受信エラー後も接続制限が保たれること、未知のsocketエラーが伝播することを確認した。
実機への書込み・製品鍵の公開・新たな課金は行わない。
