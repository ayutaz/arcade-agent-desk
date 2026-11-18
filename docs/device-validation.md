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
この節は最初の12app時点の記録。現在の接続CLI・15app・4job/期限/再接続40更新は[日常運用](daily-workflow.md)へ。物理電源の再投入と人の確認は未実施。
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

上の7手順は最初の検証経路。後続で同じ安全境界の明示CLIを実装・実機検証した。
生のsession/機器情報・資格情報・paired binaryはGit対象外に保持する。

## 音声FW追加後の互換性

2026-11-17 JST。個別許可後の音声FW1affc424…とAI Petを含む16本の環境でも、通常SoC reset後の再接続を確認した。
実CLI jobのexit0/DONE描画命令CRC、起動generationの保持、終了/HOME、radio/socket停止、音声解放、全16本の版/hash不変に成功した。
appのコード/paired packageは変更していない。実LCD/物理キー/通知音の聴取や、電池の電源断は未確認。
旧40更新の遅延値を、新FWで再測定したとは扱わない。

## 入力補正版c032と接続照合の整理

2026-11-18 JST。c032/16appでも、通常reset後の実通知/終了を確認した。
後続でPC側のメニュー照合を開始/起動直前の2回へまとめ、15回のDOWNが必要な条件でも、
実job exit0/DONE CRC、世代保持、HOME/無線停止/音声解放/16本の版/hash不変を確認。
[計測結果](device/input-offset-fast-v2.json)の接続時間は51,625.286msで、旧版との同条件速度比較ではない。
paired package/FWはこの変更で更新していない。[先行Red/Greenと初回fixture失敗](validation.md#2026-11-18-接続時のカタログ照合回数)。

## 音声v3版での限定互換性

2026-11-18。別途レビュー/個別許可したe5915861…の通常SoC reset後も、実CLIのexit0/DONE描画CRCと起動generation保持、終了/HOME・無線停止/音声解放・全16本の版/hash不変を確認した。[匿名結果](device/voice-v3-compatibility-v1.json)。接続は2回のcatalog照合/15 DOWNを含む51,853.596ms。旧版との同条件速度比較ではない。

この試験でapp/paired package/FWを変更していない。以前の40更新の遅延や他状態を再測定した結果ではなく、実LCD/物理キー/聴取・電池の電源断/実機撮影も未確認。資格情報は既存の非公開設定からRAMのみで使い、公開しない。
