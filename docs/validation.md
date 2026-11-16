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
