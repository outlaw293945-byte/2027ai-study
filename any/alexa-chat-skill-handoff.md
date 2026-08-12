# Alexa雑談スキル プロジェクト引き継ぎメモ

## やりたいこと
Alexaに話しかけると、裏でAnthropic Claude APIを呼び出して雑談の返答をしてくれるカスタムスキルを作りたい。

## 全体構成
```
ユーザーの発話
  → Alexaスキル（Amazon Developer Consoleで作成）
  → AWS Lambda（発話テキストを受け取ってClaude APIに転送）
  → Anthropic Claude API（返答を生成）
  → Lambda → Alexaが音声で読み上げ
```

## 現在の進捗状況
- [ ] Amazon Developerアカウント登録（developer.amazon.com）
- [ ] AWSアカウント登録（aws.amazon.com）
- [ ] Anthropic APIキー発行（console.anthropic.com）※Claude Proのサブスクとは別物
- [ ] Alexaスキルの作成（Custom Skill）
- [ ] Lambda関数の作成・デプロイ
- [ ] Claude API連携コードの実装
- [ ] 動作テスト

## スキル設計方針
- インテントは1つだけ：`ChatIntent`（スロットタイプ `AMAZON.SearchQuery` で自由入力を受ける）
- `shouldEndSession: false` にして、セッションを閉じずに連続で雑談できるようにする
- セッション属性（`sessionAttributes`）に会話履歴を保存し、Claude APIへの `messages` に含めて文脈を維持する
- Claude側のsystem promptで「音声で聞いて自然な長さ（2〜3文程度）」に返答を短く抑える指示を入れる（Alexaの応答タイムアウトは約8秒）
- キャラクター付けの案：三国幽玄チャンネルの世界観に寄せて、関羽っぽい口調など個性を持たせるのも面白いかもしれない

## 技術メモ
- APIキーはLambdaの環境変数に置く（コード直書き禁止）
- Lambdaのランタイムは Node.js か Python どちらでも可
- Claude APIの呼び出し先は標準の `/v1/messages` エンドポイント

## Claude Codeへのお願い
上記の構成でAlexaカスタムスキルを作りたい。まだアカウント登録の段階なら、登録手順のサポートから。登録済みなら、Lambda関数のコード作成とデプロイ手順を一緒に進めてほしい。一つずつ確認しながら丁寧に進めてください。
