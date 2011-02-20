# YOUはSHOCK
http://you-ha-shock.appspot.com

知らない誰かにひでぶと言わせるTwitter/GAEアプリ


## 使い方
1. 「使う」をクリックするとTwitter認証画面に飛びます。(認証済みの人は3へ)
2. 「許可する」を選択します。
3. 同じようにTwitter認証を登録した誰かが「ひでぶ」とか「あべし」とか言います。
4. その後、誰かが同じように「使う」た時に、あなたが「ひでぶ」とか「あべし」とか言うかもしれません。
5. 飽きたら速やかに 認証を解除 したほうがいいです。

## データの管理
./admin/edit でデータの管理ができます(要認証)。登録名と登録内容を以下に列挙します。


### oauth (必須)
OAuthの登録情報。consumer_key, consumer_secret はTwitterで登録したOAuth認証用のキーを入力してください。

<pre>
consumer_key:      *****  
consumer_secret:   *****  
oauth_callback:    http://
request_token_url: http://api.twitter.com/oauth/request_token  
access_token_url:  http://api.twitter.com/oauth/access_token  
user_auth_url:     http://api.twitter.com/oauth/authenticate  
</pre>


### words (必須)
しゃべらせる言葉

<pre>
- い？  
- ひっ!!　ひでぶっ!!  
- ひっ!!　ひでぶっ!!  
- ひでぶっ!!  
...  
</pre>


### description
タイトルの下に表示される言葉。

<pre>
- 愛で空が落ちてくるし、知らない誰かにひぶと言わせよう  
- 熱い心クサリでつないでも今は無駄だし、知らない誰かにひぶと言わせよう  
...  
</pre>


### format
ツイートの形式。 %sの部分に words がランダムで挿入される。

<pre>
%s #youhashock
</pre>


### info
お知らせ

<pre>
お知らせ：
</pre>


### suicide_rate
自爆率。連続で利用した場合の自爆率を設定します。

<pre>
- 0.00
- 0.05
- 0.10
...
</pre>


### blocklist
ブロックするユーザ。

<pre>
- mohayonao
...
</pre>
