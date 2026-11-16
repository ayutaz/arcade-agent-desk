# 開発・検証記録

## 2026-11-17: 通知と本体appの基盤

- uv/Python 3.12.13、Clang。Pythonの上限指定がない初期化では3.14が選ばれたため、.python-versionとrequires-pythonを固定してから試験をやり直した。
- protocol/runnerの先行テストは未実装moduleの欠落でRed。最小実装後7件Green（0.204秒）。実プロセスのexit 0/7、未存在コマンド、期限による停止を含む。
- C試験は最初にfixtureも不足して失敗。この試験準備の失敗はTDDのRedに数えない。mock OSとSDKを揃えた後、app.c未作成によるコンパイル失敗を意図したRedとして確認。
- C最小実装後は全12件Green（1.038秒）。Pythonで署名したpacketを実Cで処理し、generation永続化、旧起動/改ざん/逆順拒否、期限切れ、task切替、音の重複防止、BACKの早期終了、保存不可時の拒否を確認。

```sh
uv run --locked python -m unittest discover -s tests -v
```

これはホストのC mock/実プロセス試験で、本体LCD・Wi-Fi・聴取・Flash適用の結果ではない。
本体の実装済み11appへ今回のコードを配備した記録はない。GPU費用は発生させていない。

## 2026-11-17: UDP・ペアリング・CLI・配備ガード

| 変更 | 意図したRed | Green |
|---|---|---|
| UDP bridge | bridge module欠落 | 実loopback UDPの認証/世代/peer固定3件 |
| 再接続 | 失効後の新peerが固定旧peerのまま | 新世代かつ5秒失効後だけ切替 |
| pair/build | build module欠落（初回） | 固定SDK、鍵別/決定的build、16KiB上限 |
| macOS一時フォルダ | /var→/private/varで3件ValueError | 親を正規化し、鍵本体symlinkを拒否。3件成功 |
| CLI | cli module欠落 | 実exit 7が認証付きFAILとしてUDP受信、鍵非表示、不正値で未起動 |
| 専用app配備 | deploy module欠落 | 他app不変、前hash一致、HOME/キー解放、異常時停止3件 |

全unit 22件Green（1.031秒）。統合4件Green（1.024秒）。
統合の追加WASM試験は既存C実装に対する検証で、実装前TDDとは数えない。
最初のWASM試験はhelloを20msで期待して失敗したが、仕様は1秒周期のため
試験時刻を1000msへ修正。実装を試験へ合わせて変更していない。

```sh
uv run --locked python -m unittest discover -s tests -v
uv run --locked python -m unittest discover -s tests/integration -v
```

CIはLinux unitとmacOSの固定SDK/WASM buildへ分離。
本体配備ガードはmock clientで確認した段階で、実機へ書いた証拠ではない。

## 2026-11-17: 4作業と取消

| 対象 | 先行Red | Green |
|---|---|---|
| 複数job | jobs module欠落 | 実4processの0/7/成功/期限124、単一writer、全体入力検査 |
| 事前/実行中取消 | cancel引数未対応 | 起動前はchildなし、所有group終了/130 |
| 通知sink例外 | queue.Emptyを内部queueと混同して飲み込む | queue取得だけをexcept対象に限定 |
| watch CLI | subcommand欠落 | 数値結果と実失敗code、無効設定ではBridgeを開かない |
| dirty更新の集約 | 短時間の更新ごとに4通知を送る | 250msまで集約し最新4状態を送信 |

```sh
uv run --locked python -m unittest discover -s tests -p test_runner_cancel.py -v
uv run --locked python -m unittest discover -s tests -p test_jobs.py -v
uv run --locked python -m unittest discover -s tests -p test_bridge.py -q
uv run --locked python -m unittest discover -s tests -p test_cli.py -q
```

単体30件Green（1.254秒）、固定SDK547別worktreeで実WASM統合4件Green（1.074秒）。
追加したwatchと250ms集約の実機連続/再接続/通知遅延はまだ確認していない。
既存の実機通知の証拠を新CLIの実機成功へ読み替えず、FW/appを変更していない。
