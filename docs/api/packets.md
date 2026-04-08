# パケット定義一覧

`mcbe.proto.packet` モジュールで定義されるすべてのパケット ID と名前の一覧。

---

## ログイン・ハンドシェイク

| ID | 定数名 | 説明 |
|---:|---|---|
| 1 | `ID_LOGIN` | ログインリクエスト |
| 2 | `ID_PLAY_STATUS` | プレイステータス通知 |
| 3 | `ID_SERVER_TO_CLIENT_HANDSHAKE` | サーバー→クライアント暗号化ハンドシェイク |
| 4 | `ID_CLIENT_TO_SERVER_HANDSHAKE` | クライアント→サーバー暗号化ハンドシェイク |
| 5 | `ID_DISCONNECT` | 切断 |
| 143 | `ID_NETWORK_SETTINGS` | ネットワーク設定（圧縮等） |
| 193 | `ID_REQUEST_NETWORK_SETTINGS` | ネットワーク設定リクエスト |

## リソースパック

| ID | 定数名 | 説明 |
|---:|---|---|
| 6 | `ID_RESOURCE_PACKS_INFO` | リソースパック情報 |
| 7 | `ID_RESOURCE_PACK_STACK` | リソースパックスタック |
| 8 | `ID_RESOURCE_PACK_CLIENT_RESPONSE` | クライアントのパック応答 |
| 82 | `ID_RESOURCE_PACK_DATA_INFO` | パックデータ情報 |
| 83 | `ID_RESOURCE_PACK_CHUNK_DATA` | パックチャンクデータ |
| 84 | `ID_RESOURCE_PACK_CHUNK_REQUEST` | パックチャンクリクエスト |
| 340 | `ID_RESOURCE_PACKS_READY_FOR_VALIDATION` | パック検証準備完了 |

## ワールド・チャンク

| ID | 定数名 | 説明 |
|---:|---|---|
| 10 | `ID_SET_TIME` | 時刻設定 |
| 11 | `ID_START_GAME` | ゲーム開始データ |
| 58 | `ID_LEVEL_CHUNK` | レベルチャンクデータ |
| 69 | `ID_REQUEST_CHUNK_RADIUS` | チャンク描画距離リクエスト |
| 70 | `ID_CHUNK_RADIUS_UPDATED` | チャンク描画距離更新通知 |
| 121 | `ID_NETWORK_CHUNK_PUBLISHER_UPDATE` | チャンクパブリッシャー更新 |
| 174 | `ID_SUB_CHUNK` | サブチャンクデータ |
| 175 | `ID_SUB_CHUNK_REQUEST` | サブチャンクリクエスト |
| 172 | `ID_UPDATE_SUB_CHUNK_BLOCKS` | サブチャンクブロック更新 |

## エンティティ

| ID | 定数名 | 説明 |
|---:|---|---|
| 12 | `ID_ADD_PLAYER` | プレイヤー追加 |
| 13 | `ID_ADD_ACTOR` | アクター（エンティティ）追加 |
| 14 | `ID_REMOVE_ACTOR` | アクター削除 |
| 15 | `ID_ADD_ITEM_ACTOR` | アイテムエンティティ追加 |
| 16 | `ID_SERVER_PLAYER_POST_MOVE_POSITION` | プレイヤー移動後位置 |
| 17 | `ID_TAKE_ITEM_ACTOR` | アイテム取得 |
| 22 | `ID_ADD_PAINTING` | 絵画追加 |
| 39 | `ID_SET_ACTOR_DATA` | アクターデータ設定 |
| 40 | `ID_SET_ACTOR_MOTION` | アクターモーション設定 |
| 41 | `ID_SET_ACTOR_LINK` | アクターリンク設定 |
| 119 | `ID_AVAILABLE_ACTOR_IDENTIFIERS` | 利用可能なアクター識別子 |

## 移動

| ID | 定数名 | 説明 |
|---:|---|---|
| 18 | `ID_MOVE_ACTOR_ABSOLUTE` | アクター絶対移動 |
| 19 | `ID_MOVE_PLAYER` | プレイヤー移動 |
| 111 | `ID_MOVE_ACTOR_DELTA` | アクター差分移動 |
| 144 | `ID_PLAYER_AUTH_INPUT` | プレイヤー認証入力 |
| 161 | `ID_CORRECT_PLAYER_MOVE_PREDICTION` | 移動予測補正 |
| 322 | `ID_CLIENT_MOVEMENT_PREDICTION_SYNC` | 移動予測同期 |

## ブロック

| ID | 定数名 | 説明 |
|---:|---|---|
| 21 | `ID_UPDATE_BLOCK` | ブロック更新 |
| 26 | `ID_BLOCK_EVENT` | ブロックイベント |
| 34 | `ID_BLOCK_PICK_REQUEST` | ブロックピックリクエスト |
| 56 | `ID_BLOCK_ACTOR_DATA` | ブロックアクターデータ |
| 110 | `ID_UPDATE_BLOCK_SYNCED` | 同期ブロック更新 |

## インベントリ

| ID | 定数名 | 説明 |
|---:|---|---|
| 30 | `ID_INVENTORY_TRANSACTION` | インベントリトランザクション |
| 31 | `ID_MOB_EQUIPMENT` | モブ装備 |
| 32 | `ID_MOB_ARMOUR_EQUIPMENT` | モブ防具装備 |
| 46 | `ID_CONTAINER_OPEN` | コンテナ開く |
| 47 | `ID_CONTAINER_CLOSE` | コンテナ閉じる |
| 48 | `ID_PLAYER_HOT_BAR` | ホットバー |
| 49 | `ID_INVENTORY_CONTENT` | インベントリ内容 |
| 50 | `ID_INVENTORY_SLOT` | インベントリスロット |
| 51 | `ID_CONTAINER_SET_DATA` | コンテナデータ設定 |
| 145 | `ID_CREATIVE_CONTENT` | クリエイティブコンテンツ |
| 147 | `ID_ITEM_STACK_REQUEST` | アイテムスタックリクエスト |
| 148 | `ID_ITEM_STACK_RESPONSE` | アイテムスタックレスポンス |
| 162 | `ID_ITEM_REGISTRY` | アイテムレジストリ |
| 307 | `ID_SET_PLAYER_INVENTORY_OPTIONS` | インベントリオプション設定 |
| 317 | `ID_CONTAINER_REGISTRY_CLEANUP` | コンテナレジストリクリーンアップ |

## ゲームプレイ

| ID | 定数名 | 説明 |
|---:|---|---|
| 9 | `ID_TEXT` | テキストメッセージ |
| 25 | `ID_LEVEL_EVENT` | レベルイベント |
| 27 | `ID_ACTOR_EVENT` | アクターイベント |
| 28 | `ID_MOB_EFFECT` | モブエフェクト |
| 29 | `ID_UPDATE_ATTRIBUTES` | 属性更新 |
| 33 | `ID_INTERACT` | インタラクト |
| 36 | `ID_PLAYER_ACTION` | プレイヤーアクション |
| 38 | `ID_HURT_ARMOUR` | 防具ダメージ |
| 42 | `ID_SET_HEALTH` | 体力設定 |
| 43 | `ID_SET_SPAWN_POSITION` | スポーン位置設定 |
| 44 | `ID_ANIMATE` | アニメーション |
| 45 | `ID_RESPAWN` | リスポーン |
| 52 | `ID_CRAFTING_DATA` | クラフトデータ |
| 55 | `ID_ADVENTURE_SETTINGS` | アドベンチャー設定 |
| 60 | `ID_SET_DIFFICULTY` | 難易度設定 |
| 61 | `ID_CHANGE_DIMENSION` | ディメンション変更 |
| 62 | `ID_SET_PLAYER_GAME_TYPE` | ゲームモード設定 |
| 63 | `ID_PLAYER_LIST` | プレイヤーリスト |
| 65 | `ID_EVENT` | ゲームイベント |
| 66 | `ID_SPAWN_EXPERIENCE_ORB` | 経験値オーブスポーン |
| 72 | `ID_GAME_RULES_CHANGED` | ゲームルール変更 |
| 75 | `ID_SHOW_CREDITS` | クレジット表示 |
| 85 | `ID_TRANSFER` | サーバー移動 |
| 113 | `ID_SET_LOCAL_PLAYER_AS_INITIALISED` | ローカルプレイヤー初期化完了 |
| 118 | `ID_SPAWN_PARTICLE_EFFECT` | パーティクルスポーン |
| 123 | `ID_LEVEL_SOUND_EVENT` | レベルサウンドイベント |
| 129 | `ID_CLIENT_CACHE_STATUS` | クライアントキャッシュステータス |
| 151 | `ID_UPDATE_PLAYER_GAME_TYPE` | ゲームタイプ更新 |
| 156 | `ID_PACKET_VIOLATION_WARNING` | パケット違反警告 |
| 187 | `ID_UPDATE_ABILITIES` | アビリティ更新 |
| 188 | `ID_UPDATE_ADVENTURE_SETTINGS` | アドベンチャー設定更新 |
| 189 | `ID_DEATH_INFO` | 死亡情報 |

## コマンド

| ID | 定数名 | 説明 |
|---:|---|---|
| 59 | `ID_SET_COMMANDS_ENABLED` | コマンド有効化 |
| 76 | `ID_AVAILABLE_COMMANDS` | 利用可能コマンド |
| 77 | `ID_COMMAND_REQUEST` | コマンドリクエスト |
| 78 | `ID_COMMAND_BLOCK_UPDATE` | コマンドブロック更新 |
| 79 | `ID_COMMAND_OUTPUT` | コマンド出力 |
| 140 | `ID_SETTINGS_COMMAND` | 設定コマンド |

## スコアボード

| ID | 定数名 | 説明 |
|---:|---|---|
| 106 | `ID_REMOVE_OBJECTIVE` | 目標削除 |
| 107 | `ID_SET_DISPLAY_OBJECTIVE` | 表示目標設定 |
| 108 | `ID_SET_SCORE` | スコア設定 |
| 112 | `ID_SET_SCOREBOARD_IDENTITY` | スコアボードID設定 |

## UI・表示

| ID | 定数名 | 説明 |
|---:|---|---|
| 54 | `ID_GUI_DATA_PICK_ITEM` | GUI アイテムピック |
| 67 | `ID_CLIENT_BOUND_MAP_ITEM_DATA` | マップデータ |
| 68 | `ID_MAP_INFO_REQUEST` | マップ情報リクエスト |
| 73 | `ID_CAMERA` | カメラ |
| 74 | `ID_BOSS_EVENT` | ボスイベント |
| 86 | `ID_PLAY_SOUND` | サウンド再生 |
| 87 | `ID_STOP_SOUND` | サウンド停止 |
| 88 | `ID_SET_TITLE` | タイトル設定 |
| 91 | `ID_SHOW_STORE_OFFER` | ストアオファー表示 |
| 93 | `ID_PLAYER_SKIN` | プレイヤースキン |
| 100 | `ID_MODAL_FORM_REQUEST` | フォームリクエスト |
| 101 | `ID_MODAL_FORM_RESPONSE` | フォームレスポンス |
| 130 | `ID_ON_SCREEN_TEXTURE_ANIMATION` | テクスチャアニメーション |
| 138 | `ID_EMOTE` | エモート |
| 152 | `ID_EMOTE_LIST` | エモートリスト |
| 160 | `ID_PLAYER_FOG` | プレイヤーフォグ |
| 186 | `ID_TOAST_REQUEST` | トースト通知 |
| 308 | `ID_SET_HUD` | HUD 設定 |
| 310 | `ID_CLIENT_BOUND_CLOSE_FORM` | フォーム閉じ |

## カメラ（拡張）

| ID | 定数名 | 説明 |
|---:|---|---|
| 198 | `ID_CAMERA_PRESETS` | カメラプリセット |
| 300 | `ID_CAMERA_INSTRUCTION` | カメラ指示 |
| 316 | `ID_CAMERA_AIM_ASSIST` | カメラエイムアシスト |
| 320 | `ID_CAMERA_AIM_ASSIST_PRESETS` | エイムアシストプリセット |
| 321 | `ID_CLIENT_CAMERA_AIM_ASSIST` | クライアントエイムアシスト |
| 338 | `ID_CAMERA_SPLINE` | カメラスプライン |
| 339 | `ID_CAMERA_AIM_ASSIST_ACTOR_PRIORITY` | エイムアシストアクター優先度 |
| 159 | `ID_CAMERA_SHAKE` | カメラシェイク |

## Education / 特殊

| ID | 定数名 | 説明 |
|---:|---|---|
| 89 | `ID_ADD_BEHAVIOUR_TREE` | ビヘイビアツリー追加 |
| 90 | `ID_STRUCTURE_BLOCK_UPDATE` | ストラクチャブロック更新 |
| 94 | `ID_SUB_CLIENT_LOGIN` | サブクライアントログイン |
| 95 | `ID_AUTOMATION_CLIENT_CONNECT` | オートメーション接続 |
| 97 | `ID_BOOK_EDIT` | 本の編集 |
| 98 | `ID_NPC_REQUEST` | NPC リクエスト |
| 99 | `ID_PHOTO_TRANSFER` | 写真転送 |
| 109 | `ID_LAB_TABLE` | ラボテーブル |
| 117 | `ID_SCRIPT_CUSTOM_EVENT` | スクリプトイベント |
| 122 | `ID_BIOME_DEFINITION_LIST` | バイオーム定義リスト |
| 137 | `ID_EDUCATION_SETTINGS` | 教育設定 |
| 150 | `ID_CODE_BUILDER` | コードビルダー |
| 169 | `ID_NPC_DIALOGUE` | NPC ダイアログ |
| 170 | `ID_EDUCATION_RESOURCE_URI` | 教育リソース URI |
| 177 | `ID_SCRIPT_MESSAGE` | スクリプトメッセージ |
| 178 | `ID_CODE_BUILDER_SOURCE` | コードビルダーソース |
| 181 | `ID_AGENT_ACTION` | エージェントアクション |
| 190 | `ID_EDITOR_NETWORK` | エディターネットワーク |
| 304 | `ID_AGENT_ANIMATION` | エージェントアニメーション |

## ネットワーク・診断

| ID | 定数名 | 説明 |
|---:|---|---|
| 115 | `ID_NETWORK_STACK_LATENCY` | ネットワークスタックレイテンシ |
| 135 | `ID_CLIENT_CACHE_BLOB_STATUS` | キャッシュブロブステータス |
| 136 | `ID_CLIENT_CACHE_MISS_RESPONSE` | キャッシュミスレスポンス |
| 155 | `ID_DEBUG_INFO` | デバッグ情報 |
| 192 | `ID_SERVER_STATS` | サーバー統計 |
| 315 | `ID_SERVER_BOUND_DIAGNOSTICS` | 診断データ |
| 164 | `ID_CLIENT_BOUND_DEBUG_RENDERER` | デバッグレンダラー |
| 328 | `ID_DEBUG_DRAWER` | デバッグ描画 |

## その他

| ID | 定数名 | 説明 |
|---:|---|---|
| 35 | `ID_ACTOR_PICK_REQUEST` | アクターピックリクエスト |
| 64 | `ID_SIMPLE_EVENT` | シンプルイベント |
| 80 | `ID_UPDATE_TRADE` | トレード更新 |
| 81 | `ID_UPDATE_EQUIP` | 装備更新 |
| 92 | `ID_PURCHASE_RECEIPT` | 購入レシート |
| 96 | `ID_SET_LAST_HURT_BY` | 最終攻撃者設定 |
| 102 | `ID_SERVER_SETTINGS_REQUEST` | サーバー設定リクエスト |
| 103 | `ID_SERVER_SETTINGS_RESPONSE` | サーバー設定レスポンス |
| 104 | `ID_SHOW_PROFILE` | プロフィール表示 |
| 105 | `ID_SET_DEFAULT_GAME_TYPE` | デフォルトゲームタイプ設定 |
| 114 | `ID_UPDATE_SOFT_ENUM` | ソフトEnum更新 |
| 124 | `ID_LEVEL_EVENT_GENERIC` | 汎用レベルイベント |
| 125 | `ID_LECTERN_UPDATE` | 書見台更新 |
| 131 | `ID_MAP_CREATE_LOCKED_COPY` | ロックされたマップコピー |
| 132 | `ID_STRUCTURE_TEMPLATE_DATA_REQUEST` | ストラクチャテンプレートリクエスト |
| 133 | `ID_STRUCTURE_TEMPLATE_DATA_RESPONSE` | ストラクチャテンプレートレスポンス |
| 139 | `ID_MULTI_PLAYER_SETTINGS` | マルチプレイヤー設定 |
| 141 | `ID_ANVIL_DAMAGE` | 金床ダメージ |
| 142 | `ID_COMPLETED_USING_ITEM` | アイテム使用完了 |
| 146 | `ID_PLAYER_ENCHANT_OPTIONS` | エンチャントオプション |
| 149 | `ID_PLAYER_ARMOUR_DAMAGE` | 防具ダメージ |
| 153 | `ID_POSITION_TRACKING_DB_SERVER_BROADCAST` | 位置追跡DBブロードキャスト |
| 154 | `ID_POSITION_TRACKING_DB_CLIENT_REQUEST` | 位置追跡DBリクエスト |
| 157 | `ID_MOTION_PREDICTION_HINTS` | モーション予測ヒント |
| 158 | `ID_ANIMATE_ENTITY` | エンティティアニメーション |
| 163 | `ID_FILTER_TEXT` | テキストフィルタ |
| 165 | `ID_SYNC_ACTOR_PROPERTY` | アクタープロパティ同期 |
| 166 | `ID_ADD_VOLUME_ENTITY` | ボリュームエンティティ追加 |
| 167 | `ID_REMOVE_VOLUME_ENTITY` | ボリュームエンティティ削除 |
| 168 | `ID_SIMULATION_TYPE` | シミュレーションタイプ |
| 171 | `ID_CREATE_PHOTO` | 写真作成 |
| 173 | `ID_PHOTO_INFO_REQUEST` | 写真情報リクエスト |
| 176 | `ID_CLIENT_START_ITEM_COOLDOWN` | アイテムクールダウン開始 |
| 179 | `ID_TICKING_AREAS_LOAD_STATUS` | ティッキングエリアロードステータス |
| 180 | `ID_DIMENSION_DATA` | ディメンションデータ |
| 182 | `ID_CHANGE_MOB_PROPERTY` | モブプロパティ変更 |
| 183 | `ID_LESSON_PROGRESS` | レッスン進捗 |
| 184 | `ID_REQUEST_ABILITY` | アビリティリクエスト |
| 185 | `ID_REQUEST_PERMISSIONS` | パーミッションリクエスト |
| 191 | `ID_FEATURE_REGISTRY` | 機能レジストリ |
| 194 | `ID_GAME_TEST_REQUEST` | ゲームテストリクエスト |
| 195 | `ID_GAME_TEST_RESULTS` | ゲームテスト結果 |
| 196 | `ID_UPDATE_CLIENT_INPUT_LOCKS` | 入力ロック更新 |
| 197 | `ID_CLIENT_CHEAT_ABILITY` | チートアビリティ |
| 199 | `ID_UNLOCKED_RECIPES` | アンロック済みレシピ |
| 302 | `ID_TRIM_DATA` | トリムデータ |
| 303 | `ID_OPEN_SIGN` | 看板を開く |
| 305 | `ID_REFRESH_ENTITLEMENTS` | エンタイトルメント更新 |
| 306 | `ID_PLAYER_TOGGLE_CRAFTER_SLOT_REQUEST` | クラフタースロットトグル |
| 309 | `ID_AWARD_ACHIEVEMENT` | 実績付与 |
| 312 | `ID_SERVER_BOUND_LOADING_SCREEN` | ロード画面 |
| 313 | `ID_JIGSAW_STRUCTURE_DATA` | ジグソーストラクチャ |
| 314 | `ID_CURRENT_STRUCTURE_FEATURE` | 現在のストラクチャ機能 |
| 318 | `ID_MOVEMENT_EFFECT` | 移動エフェクト |
| 323 | `ID_UPDATE_CLIENT_OPTIONS` | クライアントオプション更新 |
| 324 | `ID_PLAYER_VIDEO_CAPTURE` | 動画キャプチャ |
| 325 | `ID_PLAYER_UPDATE_ENTITY_OVERRIDES` | エンティティオーバーライド更新 |
| 326 | `ID_PLAYER_LOCATION` | プレイヤー位置 |
| 327 | `ID_CLIENT_BOUND_CONTROL_SCHEME_SET` | 操作スキーム設定 |
| 329 | `ID_SERVER_BOUND_PACK_SETTING_CHANGE` | パック設定変更 |
| 330 | `ID_CLIENT_BOUND_DATA_STORE` | データストア（クライアント） |
| 331 | `ID_GRAPHICS_OVERRIDE_PARAMETER` | グラフィックスオーバーライド |
| 332 | `ID_SERVER_BOUND_DATA_STORE` | データストア（サーバー） |
| 333 | `ID_CLIENT_BOUND_DATA_DRIVEN_UI_SHOW_SCREEN` | データドリブンUI表示 |
| 334 | `ID_CLIENT_BOUND_DATA_DRIVEN_UI_CLOSE_SCREEN` | データドリブンUI閉じ |
| 335 | `ID_CLIENT_BOUND_DATA_DRIVEN_UI_RELOAD` | データドリブンUIリロード |
| 336 | `ID_CLIENT_BOUND_TEXTURE_SHIFT` | テクスチャシフト |
| 337 | `ID_VOXEL_SHAPES` | ボクセルシェイプ |
| 341 | `ID_LOCATOR_BAR` | ロケーターバー |
| 342 | `ID_PARTY_CHANGED` | パーティ変更 |
| 343 | `ID_SERVER_BOUND_DATA_DRIVEN_SCREEN_CLOSED` | データドリブン画面閉じ |
| 344 | `ID_SYNC_WORLD_CLOCKS` | ワールドクロック同期 |
| 345 | `ID_CLIENT_BOUND_ATTRIBUTE_LAYER_SYNC` | 属性レイヤー同期 |

---

## よく使用されるパケット

以下のパケットは一般的なクライアント/サーバー実装で頻繁に使用される:

- **接続**: `Login`, `PlayStatus`, `NetworkSettings`, `RequestNetworkSettings`, `Disconnect`
- **リソースパック**: `ResourcePacksInfo`, `ResourcePackStack`, `ResourcePackClientResponse`
- **ゲーム開始**: `StartGame`, `ChunkRadiusUpdated`, `RequestChunkRadius`
- **チャンク**: `LevelChunk`, `SubChunk`, `SubChunkRequest`
- **プレイヤー操作**: `PlayerAuthInput`, `MovePlayer`, `PlayerAction`, `Interact`
- **テキスト**: `Text`
- **コマンド**: `CommandRequest`, `AvailableCommands`
- **インベントリ**: `InventoryTransaction`, `ContainerOpen`, `ContainerClose`
- **UI**: `ModalFormRequest`, `ModalFormResponse`
