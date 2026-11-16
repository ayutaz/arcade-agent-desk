# 実機の自動検証

2026-11-17 JST、既存Scratch Arcade OSの保存API対応版を使用。
FWは更新せず、専用`agent-desk`だけを追加。ペアリング鍵と鍵入りpackageは公開しない。

## 結果

| 確認 | 結果 |
|---|---|
| 固定SDK build | 3,555B、16KiB以内 |
| 専用app追加 | 既存11本の版/タイトル/package hash不変、合計12本 |
| Wi-Fi/UDP | 非公開設定をRAMで使用。認証済みhello後だけ状態を送信 |
| 状態 | WORK / DONE / FAIL / WAIT / CANCEL |
| 実コマンド | exit 0→DONE、exit 7→FAIL |
| 通信停止 | 5秒TTL後にLOST |
| 描画照合 | 各状態で本体の描画命令CRCとホストの実WASM描画が一致 |
| 終了 | 期限付きFN+B論理入力でHOMEへ復帰 |
| 後処理 | catalog不変、Wi-Fi停止、audio capacity/claim/driver解放 |

これはLCDの撮影・人の見た目確認・実ボタン・通知音の聴取ではない。
再起動/再接続/長時間運用の実機試験と一括導入ツールは次工程へ残す。
ホストのmock/UDP試験だけで実機I/Oを保証した結果でもない。

## 使用した経路

1. `pair`と`build`で非公開の16B鍵と固定SDK packageを作成。
2. 公開SDKの`Client`でHOME/キー解放/11本を確認。
3. `install_owned(client, package, decode)`で専用ID追加、他app不変を照合。
4. 既存Labの試験済み`Runner`で有限の選択/起動/終了を実施。
5. `network_start`・`network_route`でRAMのみのWi-Fi/専用UDP経路を設定。
6. `Bridge`と実`run_command`で状態を送信。本体`control_status().draw_crc32`を
   同じpackageの`Session`が出す矩形命令列のCRC32と比較。
7. HOME復帰、無線停止、`audio_status`とcatalogを照合。

一回の検証手順として実行したもので、他の人向け一括導入CLIが完成したとは扱わない。
生のsession/機器情報・資格情報・paired binaryはGit対象外に保持する。
