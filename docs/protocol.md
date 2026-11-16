# 通知protocol v1

本体OSの専用UDP経路を使用。鍵16BのSipHash-2-4タグ8Bで認証する。
暗号化や機器の耐タンパー性は提供しない。公開テスト鍵での運用は禁止。

| offset | bytes | 内容 |
|---|---|---|
| 0 | 4 | ADS1 |
| 4 | 4 | generation: 1..0x7fffffff、本体appの保存slot 0を起動ごとに増分 |
| 8 | 4 | sequence: 1..0xffffffff、同一generationで共有 |
| 12 | 4 | task: 1..4 |
| 16 | 4 | elapsed_ms: uint32 |
| 20 | 1 | state: WORK=1/DONE=2/FAIL=3/WAIT=4/CANCEL=5 |
| 21 | 1 | progress: 0..100、未知は255 |
| 22 | 2 | reserved=0 |
| 24 | 4 | TTL: 1000..30000ms |
| 28 | 4 | reserved=0 |
| 32 | 8 | 先頭32Bの認証tag、little endian |

本体はADH1＋generation（各4B）＋tag8Bのhelloを送る。
保存が成功する前やgeneration枯渇時はhello/受信を許可しない。
seq差分が0または2^31以上の通知は拒否し、重複でTTLを延長しない。
LOST=6はローカル表示だけで、wire上では受け付けない。

同じgeneration/sequenceを複数送信者が共有しないように、bridge側で単一writerを管理する。
最初の認証済みhelloのIP/portへ固定し、別peerへは旧helloから5秒超かつ
strictに大きいgenerationの場合だけ切り替える。同じpeerの同じgenerationではseqを戻さない。
これは暗号学的なchallenge-responseではなく、共有鍵を持つ送信者同士の排他も保証しない。
本体からPCのコマンド実行・承認・PR操作を要求するメッセージは定義しない。

SipHashの照合値は[著者の参照vector](https://github.com/veorq/SipHash/blob/master/vectors.h)を使用。
独立した暗号監査を受けたと主張するものではない。
