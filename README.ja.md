# Arcade Agent Desk

PCで動かしている作業の状態を、Scratch Arcade本体で見る卓上端末です。
WORK・DONE・FAIL・WAIT・LOSTの表示と短い通知音を使います。
送るのは状態や数値だけで、コマンド・ソース・ログ全文は送りません。

[English](README.md)

## 現在の状態

認証付きprotocol、コマンドrunner、本体用Cアプリのホスト試験が成功しています。
UDP bridge、ペアリング/buildコマンド、実機試験、導入手順は実装中です。
**実機確認済みのリリースではありません。**

## テスト

[uv](https://docs.astral.sh/uv/)とClangを用意して実行します。

```sh
uv sync --locked
uv run --locked python -m unittest discover -s tests -v
```

Pythonは3.12.13へ固定。GPU・資格情報・実機は不要です。
実Cアプリと模擬OSをコンパイルし、実際の短い子プロセスも試験します。

## 構成

- 40Bの認証付き通知で、OSの64B UDP上限に対応。
- 起動ごとに永続generationを更新し、以前の起動の通知を拒否。
- 連番で再送攻撃・順序逆転を拒否。期限切れはLOST表示。
- 最大4件の番号付きタスクを方向ボタンで切り替え。
- runnerが実際の終了コードを通知し、実行時間を制限。

[Scratch Arcade OS](https://github.com/ayutaz/scratch-arcade-os) ABI 2向けです。
製品用のペアリング鍵はローカルだけで保持し、公開しません。
公開テスト鍵は試験専用で、実機配備には使いません。

[ホスト検証](docs/validation.md)・[通信仕様](docs/protocol.md)に詳細を記録します。
コードのライセンスは[Apache-2.0](LICENSE)です。
