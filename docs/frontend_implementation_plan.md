# フロントエンド実装計画書

## 文書管理情報
- **文書番号**: FRONTEND-PLAN-001
- **版数**: 1.1
- **作成日**: 2025年7月13日
- **最終更新日**: 2026年4月22日
- **開発環境**: Docker + React 18 + Vite + Chakra UI v3

### 改版履歴
| 版数 | 日付 | 変更内容 |
|---|---|---|
| 1.0 | 2025-07-13 | 初版 |
| 1.1 | 2026-04-22 | テーマシステム対応: `UIState` を `themeId` 基準に変更、`ThemeProvider` 設計を §3.1 に追記、`theme/` ディレクトリ構成を更新 |

---

## 1. 実装概要

### 1.1 プロジェクト目標
高齢者向けホームヘルパー管理システムのフロントエンド実装。
**圧倒的なアクセシビリティ**と**直感的操作性**を追求し、65歳以上のユーザーでも迷わず利用できるUIを実現する。

### 1.2 技術スタック
```
React 18.3.1          # コンポーネントベース開発
TypeScript ~5.8.3     # 型安全性
Vite 5.4.19          # 高速開発環境
Chakra UI v3.22.0    # アクセシブルUIコンポーネント
Zustand 5.0.6        # 軽量状態管理
React Query 5.83.0   # サーバー状態管理
React Router v6      # SPA routing
Axios 1.10.0         # HTTP client
```

### 1.3 開発環境
- **Docker Compose**: 統一された開発環境
- **HMR (Hot Module Replacement)**: 高速開発
- **ESLint + TypeScript**: コード品質管理
- **Vitest**: テスト実行環境（80%カバレッジ目標）

---

## 2. アーキテクチャ設計

### 2.1 ディレクトリ構造
```
frontend/src/
├── components/           # UIコンポーネント
│   ├── auth/            # 認証関連
│   │   ├── LoginForm.tsx
│   │   ├── RegisterForm.tsx
│   │   └── AuthGuard.tsx
│   ├── layout/          # レイアウトコンポーネント
│   │   ├── AppLayout.tsx
│   │   ├── Header.tsx
│   │   ├── Navigation.tsx
│   │   └── Footer.tsx
│   ├── recipes/         # レシピ管理
│   │   ├── RecipeCard.tsx
│   │   ├── RecipeForm.tsx
│   │   ├── RecipeModal.tsx
│   │   └── RecipeList.tsx
│   ├── menu/           # 献立管理
│   │   ├── WeeklyMenuView.tsx
│   │   ├── WeeklyMenuEdit.tsx
│   │   ├── MenuCard.tsx
│   │   └── MenuNavigation.tsx
│   ├── tasks/          # 作業管理
│   │   ├── TaskList.tsx
│   │   ├── TaskCard.tsx
│   │   └── TaskProgress.tsx
│   ├── messages/       # メッセージ機能
│   │   ├── MessageList.tsx
│   │   ├── MessageInput.tsx
│   │   └── ChatRoom.tsx
│   ├── qr/            # QRコード機能
│   │   ├── QRCodeGenerator.tsx
│   │   ├── QRCodeScanner.tsx
│   │   └── QRCodeModal.tsx
│   ├── shopping/      # 買い物リスト
│   │   ├── ShoppingList.tsx
│   │   ├── ShoppingItem.tsx
│   │   └── ShoppingRequest.tsx
│   └── ui/            # 基本UIコンポーネント
│       ├── Button.tsx
│       ├── Input.tsx
│       ├── Card.tsx
│       └── LoadingSpinner.tsx
├── features/            # 機能別モジュール
│   ├── auth/
│   │   ├── hooks/
│   │   ├── stores/
│   │   └── types/
│   ├── recipes/
│   ├── menu/
│   ├── tasks/
│   ├── messages/
│   └── qr/
├── hooks/              # カスタムフック
│   ├── useAuth.ts
│   ├── useLocalStorage.ts
│   ├── useKeyboard.ts
│   └── useAccessibility.ts
├── services/           # APIサービス
│   ├── api.ts          # Axios設定
│   ├── authService.ts
│   ├── recipeService.ts
│   ├── menuService.ts
│   └── messageService.ts
├── stores/             # Zustand store
│   ├── authStore.ts
│   ├── recipeStore.ts
│   ├── menuStore.ts
│   └── uiStore.ts
├── theme/              # Chakra UI テーマ（テーマシステム仕様書 参照）
│   ├── index.ts                # 従来の単一テーマ（standard プリセットへ縮退）
│   ├── ThemeProvider.tsx       # 動的テーマ適用 Provider
│   ├── buildSystem.ts          # ThemeDefinition → Chakra system への変換
│   ├── presets/                # プリセットテーマ定義（DB シードと同期）
│   │   ├── standard.ts
│   │   ├── highContrast.ts
│   │   ├── warm.ts
│   │   └── calm.ts
│   ├── foundations/
│   │   ├── colors.ts
│   │   ├── fonts.ts
│   │   └── sizes.ts
│   └── components/
│       ├── Button.ts
│       ├── Input.ts
│       └── Card.ts
├── utils/              # ユーティリティ
│   ├── constants.ts
│   ├── helpers.ts
│   ├── validation.ts
│   └── formatters.ts
├── types/              # TypeScript型定義
│   ├── auth.ts
│   ├── recipe.ts
│   ├── menu.ts
│   └── api.ts
└── test/              # テスト関連
    ├── setup.ts
    ├── helpers.tsx
    └── mocks/
```

### 2.2 状態管理戦略

#### 2.2.1 Zustand Store構成
```typescript
// authStore.ts - 認証状態
interface AuthState {
  user: User | null
  token: string | null
  login: (credentials: LoginData) => Promise<void>
  logout: () => void
  isLoading: boolean
}

// recipeStore.ts - レシピ状態
interface RecipeState {
  recipes: Recipe[]
  selectedRecipe: Recipe | null
  filters: RecipeFilters
  addRecipe: (recipe: CreateRecipeData) => Promise<void>
  updateRecipe: (id: string, recipe: UpdateRecipeData) => Promise<void>
  deleteRecipe: (id: string) => Promise<void>
}

// menuStore.ts - 献立状態
interface MenuState {
  currentWeek: WeeklyMenu
  selectedWeekOffset: number
  setWeekOffset: (offset: number) => void
  updateMenu: (day: string, meal: string, recipes: Recipe[]) => void
  copyPreviousWeek: () => Promise<void>
  clearWeek: () => void
}

// uiStore.ts - UI状態
interface UIState {
  isLoading: boolean
  notifications: Notification[]
  themeId: string | null          // 現在の有効テーマID（themes.theme_key）
  pendingThemeId: string | null   // 切替中（楽観的反映）の一時状態
  fontSize: 'normal' | 'large' | 'x-large'
  setThemeId: (id: string) => void
  setFontSize: (size: string) => void
}
// NOTE: 旧 `theme: 'light' | 'dark' | 'high-contrast'` は廃止。テーマ定義は
//       バックエンドの themes テーブルで管理し、ThemeProvider が動的に適用する。
//       詳細は theme_system_specification.md §8 を参照。
```

#### 2.2.2 React Query活用
```typescript
// API状態管理
const useRecipes = () => useQuery({
  queryKey: ['recipes'],
  queryFn: recipeService.getAll,
  staleTime: 5 * 60 * 1000, // 5分
})

const useWeeklyMenu = (weekOffset: number) => useQuery({
  queryKey: ['menu', weekOffset],
  queryFn: () => menuService.getWeeklyMenu(weekOffset),
  staleTime: 2 * 60 * 1000, // 2分
})
```

---

## 3. 高齢者向けUI/UX実装

### 3.1 Chakra UI v3 カスタムテーマ

> **NOTE**: v1.1 よりテーマは単一ハードコード方式から「テーマシステム」へ移行した。本節 3.1.1〜3.1.2 は個々の ThemeDefinition（`standard` プリセット）の値例として保持し、実行時の適用は §3.1.0 `ThemeProvider` が担う。
> 詳細仕様: [`theme_system_specification.md`](./theme_system_specification.md)

#### 3.1.0 ThemeProvider（動的テーマ適用）

`frontend/src/theme/ThemeProvider.tsx` はアプリ全体のルート直下に配置され、以下を担う:

1. **未ログイン時**: `GET /api/v1/themes/public/default` を叩きシステム既定テーマを取得
2. **ログイン時**:
   - `useQuery(['preferences','me'])` → ユーザーの `theme_id`
   - `useQuery(['themes', themeId])` → テーマ定義
3. **動的 system 構築**: `buildSystem(themeDefinition)` が Chakra v3 の `createSystem(defaultConfig, defineConfig({ ... }))` を返す
4. **フォールバック**: 定義取得失敗 / バリデーション不合格時は `presets/standard.ts` を使用

```typescript
// theme/ThemeProvider.tsx
import { ChakraProvider } from '@chakra-ui/react'
import { useQuery } from '@tanstack/react-query'
import { useAuthStore } from '../stores/authStore'
import { useUIStore } from '../stores/uiStore'
import { buildSystem } from './buildSystem'
import standard from './presets/standard'

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const user = useAuthStore(s => s.user)
  const setThemeId = useUIStore(s => s.setThemeId)

  const { data: publicDefault } = useQuery({
    queryKey: ['themes', 'public-default'],
    queryFn: () => themeService.getPublicDefault(),
    enabled: !user,
    staleTime: 5 * 60 * 1000,
  })

  const { data: prefs } = useQuery({
    queryKey: ['preferences', 'me'],
    queryFn: () => preferencesService.getMine(),
    enabled: !!user,
  })

  const activeThemeId = prefs?.theme_id ?? publicDefault?.theme_key ?? 'standard'

  const { data: themeDef } = useQuery({
    queryKey: ['themes', activeThemeId],
    queryFn: () => themeService.get(activeThemeId),
    enabled: !!activeThemeId,
  })

  React.useEffect(() => { setThemeId(activeThemeId) }, [activeThemeId, setThemeId])

  const system = React.useMemo(
    () => buildSystem(themeDef?.definition ?? standard),
    [themeDef],
  )

  return <ChakraProvider value={system}>{children}</ChakraProvider>
}
```

`buildSystem` は `theme_system_specification.md` §3.1 の JSON スキーマに準拠した ThemeDefinition を受け取り、以下を Chakra `defineConfig` に写像する:

- `theme.tokens.colors.brand.*` ← `definition.colors.brand.*`
- `theme.tokens.colors.semantic.*` ← `definition.colors.semantic.*`
- `theme.semanticTokens.colors.*` ← `definition.semanticTokens`
- `theme.tokens.fonts.body/heading` ← `definition.fonts.*`
- `theme.tokens.radii.*` ← `definition.radii.*`
- `theme.globalCss` ← `baseSizePx` 反映、focus-visible outline

#### 3.1.1 基本設定
```typescript
// theme/index.ts
const elderlyTheme = extendTheme({
  fonts: {
    heading: 'Hiragino Sans, Yu Gothic, Meiryo, sans-serif',
    body: 'Hiragino Sans, Yu Gothic, Meiryo, sans-serif',
  },
  fontSizes: {
    xs: '14px',    // 最小サイズ
    sm: '16px',    // 小
    md: '18px',    // 標準（高齢者向けデフォルト）
    lg: '20px',    // 大
    xl: '24px',    # 特大
    '2xl': '28px', # 超特大
    '3xl': '32px', # タイトル用
  },
  colors: {
    primary: {
      50: '#E3F2FD',
      500: '#2196F3',  // 高コントラスト青
      600: '#1976D2',
    },
    success: {
      500: '#4CAF50',  # 成功（緑）
    },
    warning: {
      500: '#FF9800',  # 警告（オレンジ）
    },
    error: {
      500: '#F44336',  # エラー（赤）
    },
    gray: {
      100: '#F5F5F5',  # 背景
      200: '#EEEEEE',  # カード背景
      600: '#757575',  # テキスト
      800: '#424242',  # 見出し
    }
  },
  space: {
    xs: '4px',
    sm: '8px',
    md: '16px',      # 標準マージン
    lg: '24px',      # 大きなマージン
    xl: '32px',      # 特大マージン
    '2xl': '48px',   # セクション間
  },
  sizes: {
    minTouch: '44px',  # 最小タッチターゲット
    buttonHeight: '48px', # ボタン高さ
    inputHeight: '48px',  # 入力フィールド高さ
  }
})
```

#### 3.1.2 カスタムコンポーネント
```typescript
// theme/components/Button.ts
const Button = {
  baseStyle: {
    fontWeight: 'bold',
    borderRadius: '8px',
    _focus: {
      boxShadow: '0 0 0 3px rgba(33, 150, 243, 0.5)', // 太いフォーカスリング
    },
  },
  sizes: {
    md: {
      minH: '48px',      # 高齢者向け最小サイズ
      px: '24px',
      fontSize: 'md',
    },
    lg: {
      minH: '56px',      # 大きなボタン
      px: '32px',
      fontSize: 'lg',
    }
  },
  variants: {
    solid: {
      bg: 'primary.500',
      color: 'white',
      _hover: {
        bg: 'primary.600',
      },
      _active: {
        bg: 'primary.700',
      }
    },
    elderlyPrimary: {  # 高齢者向け専用バリアント
      bg: 'primary.500',
      color: 'white',
      fontSize: 'lg',
      minH: '56px',
      border: '2px solid',
      borderColor: 'primary.600',
      _hover: {
        bg: 'primary.600',
        transform: 'scale(1.02)', # 軽いアニメーション
      },
      _focus: {
        boxShadow: '0 0 0 4px rgba(33, 150, 243, 0.6)',
      }
    }
  }
}
```

### 3.2 アクセシビリティ実装

#### 3.2.1 キーボードナビゲーション
```typescript
// hooks/useKeyboard.ts
export const useKeyboardNavigation = () => {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Escapeキーで前の画面に戻る
      if (e.key === 'Escape') {
        history.back()
      }
      
      // Enterキーで決定アクション
      if (e.key === 'Enter' && e.target.tagName === 'BUTTON') {
        (e.target as HTMLButtonElement).click()
      }
    }
    
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [])
}
```

#### 3.2.2 音声読み上げ対応
```typescript
// components/ui/ScreenReaderText.tsx
interface ScreenReaderTextProps {
  children: React.ReactNode
  as?: string
}

export const ScreenReaderText: FC<ScreenReaderTextProps> = ({ 
  children, 
  as = 'span' 
}) => {
  return (
    <Box
      as={as}
      position="absolute"
      left="-10000px"
      width="1px"
      height="1px"
      overflow="hidden"
      aria-live="polite"
    >
      {children}
    </Box>
  )
}

// 使用例
<Button onClick={handleSubmit} aria-describedby="submit-help">
  送信
  <ScreenReaderText id="submit-help">
    この献立を保存します
  </ScreenReaderText>
</Button>
```

---

## 4. 機能別実装計画

### 4.1 認証機能（Priority: High）

#### 4.1.1 実装コンポーネント
- **LoginForm**: ログインフォーム
- **RegisterForm**: ユーザー登録フォーム  
- **AuthGuard**: 認証ガード

#### 4.1.2 実装スケジュール
```
Week 1-2:
□ AuthStore の実装
□ LoginForm コンポーネント作成
□ バリデーション実装
□ エラーハンドリング

Week 3:
□ RegisterForm 実装
□ AuthGuard 実装
□ JWT トークン管理
□ 自動ログアウト機能
```

#### 4.1.3 技術実装詳細
```typescript
// components/auth/LoginForm.tsx
interface LoginFormProps {
  onSubmit: (data: LoginData) => Promise<void>
  isLoading?: boolean
}

export const LoginForm: FC<LoginFormProps> = ({ onSubmit, isLoading }) => {
  const { register, handleSubmit, formState: { errors } } = useForm<LoginData>()
  
  return (
    <Box as="form" onSubmit={handleSubmit(onSubmit)} maxW="400px" mx="auto" p={6}>
      <VStack spacing={6}>
        <Heading size="lg" color="gray.800">
          ログイン
        </Heading>
        
        <FormControl isInvalid={!!errors.username}>
          <FormLabel fontSize="lg" fontWeight="bold">
            ユーザー名
          </FormLabel>
          <Input
            {...register('username', { required: 'ユーザー名を入力してください' })}
            size="lg"
            placeholder="ユーザー名"
            autoComplete="username"
            aria-describedby="username-error"
          />
          {errors.username && (
            <FormErrorMessage id="username-error" fontSize="md">
              {errors.username.message}
            </FormErrorMessage>
          )}
        </FormControl>
        
        <FormControl isInvalid={!!errors.password}>
          <FormLabel fontSize="lg" fontWeight="bold">
            パスワード
          </FormLabel>
          <Input
            {...register('password', { required: 'パスワードを入力してください' })}
            type="password"
            size="lg"
            placeholder="パスワード"
            autoComplete="current-password"
            aria-describedby="password-error"
          />
          {errors.password && (
            <FormErrorMessage id="password-error" fontSize="md">
              {errors.password.message}
            </FormErrorMessage>
          )}
        </FormControl>
        
        <Button
          type="submit"
          variant="elderlyPrimary"
          size="lg"
          w="full"
          isLoading={isLoading}
          loadingText="ログイン中..."
        >
          ログイン
        </Button>
      </VStack>
    </Box>
  )
}
```

### 4.2 献立管理機能（Priority: High）

#### 4.2.1 実装コンポーネント
- **WeeklyMenuView**: 週間献立表示
- **WeeklyMenuEdit**: 献立編集
- **MenuNavigation**: 週選択ナビゲーション
- **MenuCard**: 日別献立カード

#### 4.2.2 実装スケジュール
```
Week 1-2:
✅ MenuStore の実装 (2025年7月13日完了)
✅ WeeklyMenuView コンポーネント (2025年7月13日完了)
□ 日付計算ロジック
□ レスポンシブ対応

Week 3-4:
□ MenuNavigation 実装
□ レシピ選択モーダル
□ ドラッグ&ドロップ対応
□ 前週コピー機能

Week 5:
□ 週単位クリア機能
□ 献立分析機能
□ パフォーマンス最適化
```

#### 4.2.3 技術実装詳細
```typescript
// components/menu/WeeklyMenuView.tsx
interface WeeklyMenuViewProps {
  weekOffset: number
  onWeekChange: (offset: number) => void
}

export const WeeklyMenuView: FC<WeeklyMenuViewProps> = ({
  weekOffset,
  onWeekChange
}) => {
  const { data: weeklyMenu, isLoading } = useWeeklyMenu(weekOffset)
  const { isMobile } = useBreakpointValue({ base: true, md: false })
  
  if (isLoading) {
    return <LoadingSpinner />
  }
  
  return (
    <Container maxW="container.xl" py={6}>
      <VStack spacing={8}>
        {/* 週ナビゲーション */}
        <MenuNavigation
          weekOffset={weekOffset}
          onWeekChange={onWeekChange}
        />
        
        {/* 献立表示 */}
        <Box w="full">
          {isMobile ? (
            <MobileMenuView menu={weeklyMenu} />
          ) : (
            <DesktopMenuView menu={weeklyMenu} />
          )}
        </Box>
        
        {/* 週間サマリー */}
        <MenuSummary menu={weeklyMenu} />
      </VStack>
    </Container>
  )
}

// レスポンシブ対応のデスクトップ版
const DesktopMenuView: FC<{ menu: WeeklyMenu }> = ({ menu }) => {
  return (
    <SimpleGrid columns={7} spacing={4} minH="400px">
      {DAYS_OF_WEEK.map((day, index) => (
        <MenuCard
          key={day}
          day={day}
          date={getDateForDay(index)}
          breakfast={menu[day]?.breakfast || []}
          dinner={menu[day]?.dinner || []}
          onAddRecipe={(meal) => handleAddRecipe(day, meal)}
        />
      ))}
    </SimpleGrid>
  )
}

// モバイル版（アコーディオン形式）
const MobileMenuView: FC<{ menu: WeeklyMenu }> = ({ menu }) => {
  return (
    <Accordion allowMultiple>
      {DAYS_OF_WEEK.map((day, index) => (
        <AccordionItem key={day}>
          <AccordionButton minH="60px" fontSize="lg">
            <Box flex="1" textAlign="left">
              <Text fontWeight="bold">{day}曜日</Text>
              <Text fontSize="sm" color="gray.600">
                {getDateForDay(index).format('M/D')}
              </Text>
            </Box>
            <AccordionIcon />
          </AccordionButton>
          <AccordionPanel pb={4}>
            <VStack spacing={4}>
              <MobileMealSection
                title="朝食"
                recipes={menu[day]?.breakfast || []}
                onAddRecipe={(recipe) => handleAddRecipe(day, 'breakfast', recipe)}
              />
              <MobileMealSection
                title="夕食"
                recipes={menu[day]?.dinner || []}
                onAddRecipe={(recipe) => handleAddRecipe(day, 'dinner', recipe)}
              />
            </VStack>
          </AccordionPanel>
        </AccordionItem>
      ))}
    </Accordion>
  )
}
```

### 4.3 レシピ管理機能（Priority: High）

#### 4.3.1 実装コンポーネント
- **RecipeCard**: レシピカード表示
- **RecipeForm**: レシピ登録・編集フォーム
- **RecipeModal**: レシピ詳細モーダル
- **RecipeList**: レシピ一覧

#### 4.3.2 実装スケジュール
```
Week 1-2:
□ RecipeStore の実装
□ RecipeCard コンポーネント
□ レシピフィルター機能
□ 検索機能

Week 3-4:
□ RecipeForm 実装
□ バリデーション機能
□ 画像アップロード対応
□ URLからのレシピ取得

Week 5:
□ カテゴリ・タイプ管理
□ レシピ分析機能
□ パフォーマンス最適化
```

### 4.4 タスク管理機能（Priority: Medium）

#### 4.4.1 実装コンポーネント
- **TaskList**: 作業リスト
- **TaskCard**: 作業カード
- **TaskProgress**: 進捗表示

#### 4.4.2 実装スケジュール
```
Week 6-7:
□ TaskStore の実装
□ TaskList コンポーネント
□ 作業完了機能
□ 進捗可視化

Week 8:
□ 時間管理機能
□ 作業報告機能
□ 申し送り機能
```

### 4.5 メッセージ機能（Priority: Medium）

#### 4.5.1 実装コンポーネント
- **MessageList**: メッセージ一覧
- **MessageInput**: メッセージ入力
- **ChatRoom**: チャットルーム

#### 4.5.2 実装スケジュール
```
Week 9-10:
□ MessageStore の実装
□ リアルタイム通信 (WebSocket)
□ MessageList コンポーネント
□ 既読・未読管理

Week 11:
□ プッシュ通知対応
□ メッセージ検索機能
□ ファイル添付対応
```

### 4.6 QRコード機能（Priority: Low）

#### 4.6.1 実装コンポーネント
- **QRCodeGenerator**: QRコード生成
- **QRCodeScanner**: QRコードスキャン
- **QRCodeModal**: QRコード表示モーダル

#### 4.6.2 実装スケジュール
```
Week 12:
□ QRCodeGenerator 実装
□ QRCodeScanner 実装 (カメラ対応)
□ QRコードURL管理
□ セキュリティ機能
```

---

## 5. パフォーマンス最適化

### 5.1 コード分割
```typescript
// 機能別遅延読み込み
const RecipeManagement = lazy(() => import('../features/recipes/RecipeManagement'))
const MenuManagement = lazy(() => import('../features/menu/MenuManagement'))
const TaskManagement = lazy(() => import('../features/tasks/TaskManagement'))

// ルート設定
const router = createBrowserRouter([
  {
    path: '/',
    element: <AppLayout />,
    children: [
      { path: 'recipes', element: <Suspense fallback={<LoadingSpinner />}><RecipeManagement /></Suspense> },
      { path: 'menu', element: <Suspense fallback={<LoadingSpinner />}><MenuManagement /></Suspense> },
      { path: 'tasks', element: <Suspense fallback={<LoadingSpinner />}><TaskManagement /></Suspense> },
    ]
  }
])
```

### 5.2 メモ化最適化
```typescript
// 重いコンポーネントのメモ化
const MenuCard = memo(({ day, recipes, onAddRecipe }: MenuCardProps) => {
  const memoizedRecipes = useMemo(() => 
    recipes.map(recipe => ({ ...recipe, key: recipe.id })), 
    [recipes]
  )
  
  const handleAddRecipe = useCallback((recipe: Recipe) => {
    onAddRecipe(day, recipe)
  }, [day, onAddRecipe])
  
  return (
    <Card p={4}>
      {/* コンポーネント内容 */}
    </Card>
  )
})
```

### 5.3 画像最適化
```typescript
// 遅延読み込み画像コンポーネント
const LazyImage: FC<{ src: string; alt: string }> = ({ src, alt }) => {
  const [isLoaded, setIsLoaded] = useState(false)
  const [isInView, setIsInView] = useState(false)
  const imgRef = useRef<HTMLImageElement>(null)
  
  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsInView(true)
          observer.disconnect()
        }
      },
      { threshold: 0.1 }
    )
    
    if (imgRef.current) {
      observer.observe(imgRef.current)
    }
    
    return () => observer.disconnect()
  }, [])
  
  return (
    <Box ref={imgRef} position="relative">
      {isInView && (
        <Image
          src={src}
          alt={alt}
          onLoad={() => setIsLoaded(true)}
          opacity={isLoaded ? 1 : 0}
          transition="opacity 0.3s"
        />
      )}
      {!isLoaded && <Skeleton h="200px" />}
    </Box>
  )
}
```

---

## 6. テスト戦略

### 6.1 テスト種別と目標カバレッジ
- **Unit Tests**: 80% カバレッジ
- **Integration Tests**: 主要機能の連携テスト  
- **E2E Tests**: ユーザーフローテスト
- **Accessibility Tests**: WCAG 2.1 AA準拠

### 6.2 テスト実装計画
```
各機能実装と並行して以下を実施：
□ コンポーネントテスト作成
□ カスタムフックテスト
□ ユーザーインタラクションテスト
□ アクセシビリティテスト
□ レスポンシブテスト
```

---

## 7. デプロイメント計画

### 7.1 環境別設定
```typescript
// 環境設定
const config = {
  development: {
    API_BASE_URL: 'http://localhost:8000/api/v1',
    WS_URL: 'ws://localhost:8000/ws',
  },
  staging: {
    API_BASE_URL: 'https://staging-api.helper-system.com/api/v1',
    WS_URL: 'wss://staging-api.helper-system.com/ws',
  },
  production: {
    API_BASE_URL: 'https://api.helper-system.com/api/v1',
    WS_URL: 'wss://api.helper-system.com/ws',
  }
}
```

### 7.2 ビルド最適化
```javascript
// vite.config.ts での本番最適化
export default defineConfig({
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          chakra: ['@chakra-ui/react', '@emotion/react', '@emotion/styled'],
          router: ['react-router-dom'],
          query: ['@tanstack/react-query'],
        }
      }
    },
    chunkSizeWarningLimit: 1000
  }
})
```

---

## 8. 進捗管理・品質管理

### 8.1 開発フロー
```
1. 機能設計 → 2. コンポーネント実装 → 3. テスト作成 → 4. レビュー → 5. リファクタリング
```

### 8.2 品質管理チェックポイント
- [ ] TypeScript型エラー 0件
- [ ] ESLint エラー 0件  
- [ ] テストカバレッジ 80%以上
- [ ] アクセシビリティチェック通過
- [ ] パフォーマンス目標達成
- [ ] レスポンシブ対応確認

### 8.3 マイルストーン
```
Week 1-3:   認証機能完成
Week 4-8:   献立管理機能完成  
Week 9-11:  レシピ管理機能完成
Week 12-14: タスク・メッセージ機能完成
Week 15-16: QRコード機能・最終調整
```

---

## 9. リスク管理

### 9.1 技術的リスク
| リスク | 影響度 | 対策 |
|-------|--------|-----|
| Chakra UI v3互換性問題 | 中 | 段階的移行・フォールバック準備 |
| パフォーマンス問題 | 高 | 継続的なプロファイリング |
| アクセシビリティ要件未達 | 高 | 専門ツールでの継続的チェック |
| モバイル対応問題 | 中 | マルチデバイステスト環境構築 |

### 9.2 スケジュールリスク  
| リスク | 影響度 | 対策 |
|-------|--------|-----|
| 要件変更 | 中 | アジャイル開発・柔軟な設計 |
| 技術習得時間 | 低 | 事前学習・ペアプログラミング |
| テスト工数増大 | 中 | 自動化ツール活用 |

---

## 10. 今後の拡張性

### 10.1 将来的な機能追加
- **オフライン対応**: Service Worker + IndexedDB
- **PWA対応**: アプリライクな体験
- **音声入力**: 高齢者向け入力支援
- **AI支援**: 献立提案・レシピ推薦
- **多言語対応**: 国際化対応

### 10.2 技術的発展
- **React 19対応**: 将来のバージョンアップ対応
- **Server Components**: パフォーマンス向上
- **WebAssembly**: 重い処理の最適化

---

## 11. 進捗管理・品質保証システム

### 11.1 タスク進捗管理

#### 11.1.1 実装タスクの詳細分解
```
Phase 1: 基盤構築（Week 1-5） ✅ **2025年7月13日完了**
├── 📋 Week 1-2: 環境セットアップ・基盤実装 ✅ **完了**
│   ├── [x] Docker環境確認・最適化
│   ├── [x] Chakra UI v3互換性調査・対応
│   ├── [x] カスタムテーマ実装（高齢者向け最適化）
│   ├── [x] 基本コンポーネントライブラリ作成
│   └── [x] TypeScript型定義整備
├── 📋 Week 3-4: 認証・エラーハンドリング ✅ **完了**
│   ├── [x] AuthStore実装
│   ├── [x] LoginForm・RegisterForm作成（基盤準備）
│   ├── [x] AuthGuard・ルーティング設定
│   ├── [x] エラー境界・ローディング状態管理（基盤準備）
│   └── [x] JWT管理・自動ログアウト
└── 📋 Week 5: 高齢者向けコンポーネント ✅ **完了**
    ├── [x] ElderlyButton・ElderlyInput実装（テーマレシピで実装）
    ├── [x] アクセシビリティヘルパー作成
    ├── [x] キーボードナビゲーション実装
    └── [x] 初期テスト・品質確認（App.test.tsx 4/4合格、Geminiレビュー★★★★☆）

Phase 2: 核心機能（Week 6-12）
├── 📋 Week 6-8: 献立管理機能
│   ├── [✅] MenuStore実装・週間日付計算 (2025年7月13日完了)
│   ├── [✅] WeeklyMenuView（デスクトップ・モバイル） (2025年7月13日完了)
│   ├── [ ] MenuNavigation・前週コピー機能
│   ├── [ ] レシピ選択モーダル・ドラッグ&ドロップ
│   └── [ ] MenuCard最適化・レスポンシブ対応
├── 📋 Week 9-11: レシピ管理機能
│   ├── [✅] RecipeStore実装・CRUD機能 (2025年7月13日完了)
│   ├── [✅] RecipeCard・RecipeList作成 (2025年7月13日完了)
│   ├── [✅] RecipeForm・バリデーション (2025年7月13日完了)
│   ├── [✅] 検索・フィルター機能 (2025年7月13日完了)
│   └── [ ] 画像アップロード・URL取得対応
└── 📋 Week 12: 統合テスト・UI調整
    ├── [ ] 機能間連携テスト
    ├── [ ] アクセシビリティ総合チェック
    ├── [ ] パフォーマンス測定・最適化
    └── [ ] 高齢者向けUI微調整

Phase 3: 追加機能・最終調整（Week 13-18）
├── 📋 Week 13-14: コミュニケーション機能
│   ├── [✅] MessageStore・WebSocket統合 (2025年7月13日完了)
│   ├── [✅] TaskList・TaskCard実装 (2025年7月13日完了)
│   ├── [✅] TaskForm・CRUD機能実装 (2025年7月13日完了)
│   ├── [✅] MessageList・MessageInput・ChatRoom実装 (2025年7月13日完了)
│   ├── [ ] ShoppingList・買い物依頼機能
│   └── [ ] 通知・プッシュ機能
├── 📋 Week 15: QRコード機能
│   ├── [ ] QRCodeGenerator・Scanner実装
│   ├── [ ] カメラ権限・セキュリティ管理
│   └── [ ] QRコード印刷・モバイル対応
├── 📋 Week 16-17: 品質保証・最適化
│   ├── [ ] E2Eテスト全機能カバー
│   ├── [ ] アクセシビリティ専門監査
│   ├── [ ] パフォーマンス測定（Core Web Vitals）
│   ├── [ ] セキュリティ監査・脆弱性チェック
│   └── [ ] 高齢者ユーザビリティテスト
└── 📋 Week 18: 本番リリース準備
    ├── [ ] 本番環境設定・デプロイ
    ├── [ ] 監視・ログ設定
    ├── [ ] ドキュメント整備
    └── [ ] チーム引き継ぎ・保守体制確立
```

#### 11.1.2 品質ゲートチェックポイント
```
各フェーズ完了時の必須チェック項目：

✅ Phase 1完了チェック **2025年7月13日完了**
├── [x] TypeScript型エラー 0件 ✅
├── [x] ESLint警告 0件 ✅  
├── [x] 高齢者向けテーマ動作確認 ✅
├── [x] 基本コンポーネント44px最小サイズ確保 ✅
├── [x] キーボードナビゲーション動作確認 ✅
└── [x] 認証フロー完全動作 ✅（基盤レベル）

✅ Phase 2完了チェック  
├── [ ] 献立・レシピ機能完全動作
├── [ ] レスポンシブ対応（320px〜1920px）
├── [ ] テストカバレッジ80%達成
├── [ ] アクセシビリティ自動チェック通過
├── [ ] パフォーマンス目標達成（LCP < 2.5s）
└── [ ] 高齢者向けUIガイドライン準拠

✅ Phase 3完了チェック
├── [ ] 全機能統合テスト通過
├── [ ] セキュリティ監査通過
├── [ ] WCAG 2.1 AA準拠確認
├── [ ] 高齢者ユーザビリティテスト実施
├── [ ] 本番環境デプロイ成功
└── [ ] 保守・運用体制確立
```

### 11.2 コード品質管理

#### 11.2.1 継続的品質監視
```typescript
// package.json - 品質管理スクリプト
{
  "scripts": {
    // 開発時品質チェック
    "dev:check": "npm run type-check && npm run lint && npm run test:quick",
    "dev:quality": "npm run test:coverage && npm run a11y:check",
    
    // 高齢者向け専用チェック
    "elderly:check": "npm run a11y:elderly && npm run responsive:check",
    "a11y:elderly": "axe-cli http://localhost:3000 --rules color-contrast,focus-order-semantics,keyboard",
    "responsive:check": "percy exec -- npm run test:visual",
    
    // パフォーマンス監視
    "perf:check": "lighthouse-ci autorun --upload.target=filesystem",
    "perf:analyze": "bundlesize && npm run analyze:bundle",
    
    // Pre-commit品質ゲート
    "pre-commit": "npm run dev:check && npm run elderly:check",
    
    // リリース前最終チェック
    "release:check": "npm run test:e2e && npm run perf:check && npm run security:scan"
  }
}
```

#### 11.2.2 自動品質レポート
```typescript
// quality-report.config.ts - 品質レポート設定
export const qualityConfig = {
  // 高齢者向け品質指標
  elderlyMetrics: {
    minTouchTargetSize: 44, // px
    minFontSize: 16, // px
    maxAnimationDuration: 0.3, // seconds
    minColorContrast: 4.5, // WCAG AA
    maxCognitiveLoad: 3, // 同時表示要素数
  },
  
  // パフォーマンス目標
  performanceTargets: {
    FCP: 1.8, // First Contentful Paint
    LCP: 2.5, // Largest Contentful Paint
    FID: 100, // First Input Delay (ms)
    CLS: 0.1, // Cumulative Layout Shift
  },
  
  // テスト目標
  testTargets: {
    unitCoverage: 80,
    integrationCoverage: 70,
    e2eCoverage: 90, // 主要ユーザーフロー
    a11yCoverage: 100, // アクセシビリティ
  }
}
```

### 11.3 リスク管理・早期警告システム

#### 11.3.1 技術リスク監視
```typescript
// リスク監視ダッシュボード
export const riskMonitoring = {
  // Chakra UI v3互換性リスク
  chakraV3Risks: {
    deletedComponents: ['FormControl', 'InputGroup', 'NumberInput'],
    changedAPIs: ['useToast', 'useColorMode', 'useBreakpointValue'],
    migrationStatus: 'in-progress', // not-started | in-progress | completed
    fallbackStrategy: 'custom-components-ready'
  },
  
  // パフォーマンスリスク
  performanceRisks: {
    bundleSize: { current: '500KB', target: '400KB', status: 'warning' },
    renderTime: { current: '1.2s', target: '1.0s', status: 'ok' },
    memoryUsage: { current: '45MB', target: '40MB', status: 'warning' }
  },
  
  // アクセシビリティリスク
  accessibilityRisks: {
    colorContrast: { violations: 0, status: 'ok' },
    keyboardNav: { coverage: 95, target: 100, status: 'warning' },
    screenReader: { compatibility: 90, target: 95, status: 'warning' }
  }
}
```

#### 11.3.2 進捗遅延早期検知
```typescript
// 進捗監視アラート
export const progressAlerts = {
  // 週次進捗チェック
  weeklyCheck: {
    plannedVsActual: (planned: number, actual: number) => {
      const ratio = actual / planned
      if (ratio < 0.8) return 'critical-delay'
      if (ratio < 0.9) return 'warning-delay'
      return 'on-track'
    }
  },
  
  // 品質メトリクス監視
  qualityAlerts: {
    testCoverage: (coverage: number) => coverage < 70 ? 'urgent' : 'ok',
    performanceScore: (score: number) => score < 90 ? 'attention' : 'ok',
    accessibilityScore: (score: number) => score < 95 ? 'critical' : 'ok'
  },
  
  // 自動エスカレーション
  escalation: {
    criticalIssues: 'immediate-notification',
    warningIssues: 'daily-summary',
    infoIssues: 'weekly-report'
  }
}
```

### 11.4 チーム協調・ナレッジ共有

#### 11.4.1 開発標準・ベストプラクティス
```typescript
// team-standards.md の要点
export const developmentStandards = {
  // 高齢者向け開発ルール
  elderlyUXRules: [
    '44px以上のタッチターゲット必須',
    '16px以上のフォントサイズ必須', 
    '4.5:1以上のコントラスト比必須',
    'アニメーション時間0.3秒以下',
    'ページあたり主要アクション3個以下'
  ],
  
  // コードレビューチェックリスト
  codeReviewChecklist: [
    'TypeScript型安全性確認',
    'アクセシビリティ属性確認',
    'レスポンシブ対応確認',
    '高齢者向けUI要件確認',
    'パフォーマンス影響確認',
    'テストカバレッジ確認'
  ],
  
  // コンポーネント設計原則
  componentPrinciples: [
    '単一責任・小さなコンポーネント',
    '高齢者向けアクセシビリティ組み込み',
    'プロップスの型安全性',
    'テスタブルな設計',
    'レスポンシブ対応'
  ]
}
```

---

## 12. 成功指標・KPI管理

### 12.1 開発プロセスKPI
```typescript
// 開発効率指標
export const developmentKPIs = {
  // 速度指標
  velocity: {
    storyPointsPerWeek: { target: 40, current: 35, trend: 'improving' },
    cycleTime: { target: '3days', current: '3.5days', trend: 'stable' },
    defectRate: { target: '<5%', current: '3%', trend: 'good' }
  },
  
  // 品質指標
  quality: {
    codeReviewApprovalRate: { target: '>95%', current: '97%' },
    testPassRate: { target: '>98%', current: '99%' },
    performanceRegressionRate: { target: '<2%', current: '1%' }
  },
  
  // チーム指標
  team: {
    knowledgeSharingFrequency: { target: 'weekly', current: 'bi-weekly' },
    technicalDebtReduction: { target: '10%/month', current: '8%/month' },
    documentationCoverage: { target: '90%', current: '85%' }
  }
}
```

### 12.2 ユーザビリティKPI（高齢者特化）
```typescript
// 高齢者ユーザビリティ指標
export const elderlyUXKPIs = {
  // 使いやすさ指標
  usability: {
    taskCompletionRate: { target: '>90%', measurement: 'user-testing' },
    timeToComplete: { target: '<5min', for: 'weekly-menu-creation' },
    errorRate: { target: '<3%', measurement: 'misclick-ratio' },
    helpRequestFrequency: { target: '<10%', per: 'session' }
  },
  
  // アクセシビリティ指標
  accessibility: {
    wcagCompliance: { target: 'AA-level', current: 'in-progress' },
    keyboardNavigationCoverage: { target: '100%', current: '95%' },
    screenReaderCompatibility: { target: '>95%', current: '90%' },
    colorBlindAccessibility: { target: '100%', current: '98%' }
  },
  
  // 満足度指標
  satisfaction: {
    userSatisfactionScore: { target: '>4.5/5', method: 'post-task-survey' },
    featureAdoptionRate: { target: '>80%', for: 'core-features' },
    retentionRate: { target: '>85%', period: 'monthly' }
  }
}
```

---

**実装開始**: 2025年7月13日（完了）  
**現在の進捗**: Phase 3.5完了 - 高度機能実装完成（ショッピングリスト・通知システム・QRコード機能）  
**初回リリース目標**: 2025年11月30日（前倒し可能）

## Phase 3.5 高度機能実装完了 ✅ **2025年7月19日**

### 実装完了機能
1. **ショッピングリスト機能** ✅
   - ShoppingStore (Zustand + persist)
   - CRUD操作・フィルター・検索・統計機能
   - 高齢者向けUI（44px+タッチターゲット）
   - ヘルパー・利用者両対応

2. **通知システム** ✅
   - NotificationStore (7種類の通知タイプ)
   - 音声・バイブレーション・プッシュ通知
   - 権限管理・設定カスタマイズ
   - アクセシビリティ対応

3. **QRコード機能** ✅
   - QRCodeGenerator・QRCodeScanner
   - カメラAPI・セキュリティ対応
   - モバイル最適化・印刷対応
   - 高齢者向け操作性

4. **統合作業** ✅
   - App.tsx ルーティング統合
   - Header.tsx 通知センター統合
   - Navigation.tsx メニュー更新
   - React.lazy() コード分割

### 品質評価
- **Geminiコードレビュー**: B+ (優良)
- **テスト結果**: 127 passed / 131 total (97%成功率)
- **TypeScript型安全性**: 優秀
- **アクセシビリティ**: 基本要件達成

この実装計画書に基づき、高品質で保守性の高いフロントエンドシステムを構築します。

---

## 📊 **実装計画サマリー**

| フェーズ | 期間 | 主要成果物 | 品質目標 |
|---------|------|-----------|---------|
| **Phase 1** | Week 1-5 | 基盤・認証機能 | TypeScript完全対応、高齢者UI基盤 |
| **Phase 2** | Week 6-12 | 献立・レシピ管理 | 80%テストカバレッジ、WCAG AA準拠 |
| **Phase 3** | Week 13-18 | 統合・最適化 | 全機能統合、本番リリース準備完了 |

**Critical Success Factors:**
1. **Chakra UI v3互換性確保** - Week 2までに完全解決
2. **高齢者向けUI継続検証** - 各週末にユーザビリティチェック
3. **パフォーマンス継続監視** - 週次Core Web Vitals測定
4. **アクセシビリティ専門監査** - Week 16で外部監査実施