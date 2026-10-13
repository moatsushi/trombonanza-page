# Google App Engine + Google Apps Scriptへのデプロイ

サイト本体はFlaskで静的HTMLを生成し、Google App Engineのstatic handlerから配信します。
お問い合わせだけをApp Engine上のFlask APIで受け取り、Google Apps Scriptへ安全に中継して
設定した非公開の宛先へメール送信します。Cloudflareは使用しません。

```text
ブラウザー
  -> Google App Engine /api/contact
  -> Google Apps Script Web App
  -> 設定した宛先
```

## 1. Apps Scriptを用意する

1. メール送信元として使用するアカウントで
   [Google Apps Script](https://script.google.com/)の新しいプロジェクトを作成します。
2. `google-apps-script/Code.gs` をエディターへ貼り付けます。
3. プロジェクト設定で「`appsscript.json` マニフェスト ファイルをエディタで表示する」を有効にし、
   `google-apps-script/appsscript.json` の内容へ置き換えます。
4. 十分に長い共有シークレットを生成します。

   ```sh
   python3 -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

5. Apps Scriptの「プロジェクトの設定」>「スクリプト プロパティ」に次を登録します。

   - プロパティ: `CONTACT_SHARED_SECRET`
   - 値: 上で生成した共有シークレット
   - プロパティ: `CONTACT_RECIPIENT`
   - 値: お問い合わせの送信先メールアドレス

6. 「デプロイ」>「新しいデプロイ」>「ウェブアプリ」を選び、次の設定でデプロイします。

   - 次のユーザーとして実行: 自分
   - アクセスできるユーザー: 全員

7. メール送信権限を承認し、末尾が `/exec` のウェブアプリURLを控えます。

共有シークレット、ウェブアプリURL、送信先メールアドレスは公開HTMLやGitへ保存しません。
Apps Script側で送信先をスクリプトプロパティに固定し、訪問者が変更できないようにしています。

## 2. ローカルで確認する

```sh
python3 -m pip install -r requirements.txt
python3 -m unittest discover -s tests
python3 build_static.py
python3 app.py
```

`http://127.0.0.1:5001` からフォームをテストする場合は、次の環境変数も設定して起動します。

```sh
APPS_SCRIPT_WEB_APP_URL="https://script.google.com/macros/s/.../exec" \
APPS_SCRIPT_SHARED_SECRET="生成した共有シークレット" \
python3 app.py
```

## 3. App Engineへデプロイする

Google Cloud CLIで従来使用しているプロジェクトを選択してから実行します。

```sh
gcloud config set project YOUR_PROJECT_ID

APPS_SCRIPT_WEB_APP_URL="https://script.google.com/macros/s/.../exec" \
APPS_SCRIPT_SHARED_SECRET="生成した共有シークレット" \
python3 deploy_gae.py --project=trombonanza-page
```

`deploy_gae.py` は次を自動実行します。

1. `concert.sqlite` とテンプレートから `dist/` を生成
2. 秘密情報を一時的なApp Engine設定ファイルへ追加
3. `gcloud app deploy` を実行
4. 一時設定ファイルを削除

静的ページはApp Engineインフラから直接配信され、`/api/contact` だけがPythonランタイムへ
到達します。フォームには入力検証、送信元チェック、サイズ制限、ボット用ハニーポット、
Apps Script Cacheを使った送信元ごとの回数制限（1分間に5件）を実装しています。

## 更新方法

演奏会情報、テンプレート、CSSなどを変更した後も、手順3と同じコマンドで再生成・
デプロイします。Apps Scriptコードを変更した場合は「デプロイを管理」から新しいバージョンへ
更新してください。
