# 4作業をまとめて監視

2026-11-17。ホストの複数作業CLI。今回の追加部分はまだ実機の連続試験をしていない。

```sh
uv run --locked python -m arcade_agent_desk watch \
  --key secrets/pairing.json --jobs examples/jobs.json --linger 3
```

サンプルはunit試験・2秒待機・意図したexit7・意図した期限切れの4本。
失敗を含むため終了コードは1。全成功だけ0、入力不正は2。
実作業へ使う場合はGit対象外の`secrets/jobs.json`へコピーし、実行するargvと期限を設定する。
シェル展開は使わず、1〜4の重複しないtask IDへ固定する。最大4並行、各期限1時間以内。

| イベント | 表示 |
|---|---|
| 実行中 | WORK |
| exit0 | DONE |
| 非0 / 起動失敗 / 期限 | FAIL |
| 取消 | CANCEL |
| 送信が止まりTTL経過 | LOST |

全jobを検査してから起動。WORKの送信後も実exitを待ち、失敗を完了と誤表示しない。
Ctrl-Cは所有するjob groupだけを終了する。通知内容はtask番号/状態/経過時間等で、
command・stdout・資格情報はUDPへ含めない。子コマンドの出力はローカルの端末へ出る。
WAITは既存libraryの明示イベントのみで、watchがAIの承認待ちを推測することはない。

Bridgeへの書き込みは1スレッドにまとめる。頻繁なdirty更新を250ms単位でまとめ、
1回最大4通知、heartbeatは500ms。認証済みHELLOには既存の即時応答を維持する。
この上限は実機の欠落0/遅延の保証ではなく、連続試験で別に測定する。

実機は同じ鍵でbuildしたapp、RAM Wi-FiとUDP route、明示したLAN bindが必要。
watch単独では実機へinstall/接続しない。配備と接続の一般向けCLIは次の工程。
