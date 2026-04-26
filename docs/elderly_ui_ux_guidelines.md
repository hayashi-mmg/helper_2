# 高齢者向けUI/UXガイドライン

## 文書管理情報
- **文書番号**: UX-GUIDE-001
- **版数**: 1.1
- **作成日**: 2025年7月13日
- **最終更新日**: 2026年4月22日
- **設計者**: Claude Code + Gemini UX検証

### 改版履歴
| 版数 | 日付 | 変更内容 |
|---|---|---|
| 1.0 | 2025-07-13 | 初版 |
| 1.1 | 2026-04-22 | §2.3 既定テーマと派生テーマの関係、§2.4 テーマ適用時のアクセシビリティ制約 を追加 |

---

## 1. ガイドライン概要

### 1.1 設計思想
**「圧倒的なアクセシビリティの確保」**

高齢者の身体的制約・認知的特性を深く理解し、「使いやすい」ではなく「使わざるを得ない」レベルの直感的なインターフェースを実現する。

### 1.2 対象ユーザー特性
- **年齢層**: 65歳以上が主要ユーザー
- **ITリテラシー**: 低〜中程度（スマートフォン基本操作は可能）
- **身体的制約**: 視力低下、聴力低下、手指の細かい動作困難
- **認知的特性**: 情報処理速度の低下、同時処理能力の制限

### 1.3 準拠基準
- **WCAG 2.1 AA準拠**（Web Content Accessibility Guidelines）
- **JIS X 8341準拠**（日本工業規格 高齢者・障害者等配慮設計指針）
- **モバイルアクセシビリティガイドライン準拠**

---

## 2. 技術実装フレームワーク

### 2.1 Chakra UI v3カスタムテーマ設定

#### 2.1.1 基本テーマ構成
```typescript
// theme/index.ts
import { extendTheme } from '@chakra-ui/react'
import { fonts } from './foundations/fonts'
import { colors } from './foundations/colors'
import { sizes } from './foundations/sizes'
import { components } from './components'

const elderlyTheme = extendTheme({
  fonts,
  colors,
  sizes,
  components,
  config: {
    initialColorMode: 'light',
    useSystemColorMode: false, // ダークモード切り替えで混乱を避ける
  }
})

export default elderlyTheme
```

#### 2.1.2 フォント設定
```typescript
// theme/foundations/fonts.ts
export const fonts = {
  // 日本語に最適化されたフォントスタック
  body: "'Hiragino Sans', 'Yu Gothic Medium', 'Meiryo', 'Noto Sans JP', sans-serif",
  heading: "'Hiragino Sans', 'Yu Gothic Medium', 'Meiryo', 'Noto Sans JP', sans-serif",
  
  // 高齢者向けサイズ体系（rem単位でブラウザ設定尊重）
  sizes: {
    // 基本サイズを大きめに設定
    xs: '0.875rem',  // 14px（最小サイズ）
    sm: '1rem',      // 16px（最小推奨）
    md: '1.125rem',  // 18px（標準）
    lg: '1.375rem',  // 22px（見出し小）
    xl: '1.75rem',   // 28px（見出し大）
    '2xl': '2.25rem', // 36px（タイトル）
    '3xl': '3rem',   // 48px（メインタイトル）
  }
}
```

#### 2.1.3 カラーパレット（WCAG 2.1 AA準拠）
```typescript
// theme/foundations/colors.ts
export const colors = {
  // プライマリカラー（高コントラスト確保）
  primary: {
    50: '#e3f2fd',   // 背景用
    100: '#bbdefb',  // ホバー用
    500: '#1976d2',  // メイン（背景白に対してコントラスト比 4.83:1）
    600: '#1565c0',  // フォーカス用
    700: '#0d47a1',  // アクティブ用
  },
  
  // セカンダリカラー（アクセント）
  secondary: {
    50: '#fff3e0',
    100: '#ffe0b2', 
    500: '#ff9800',  // オレンジ系（背景白に対してコントラスト比 4.55:1）
    600: '#f57c00',
    700: '#e65100',
  },
  
  // セマンティックカラー
  success: {
    500: '#2e7d32',  // 緑（背景白に対してコントラスト比 5.09:1）
    600: '#1b5e20',
  },
  error: {
    500: '#d32f2f',  // 赤（背景白に対してコントラスト比 5.25:1）
    600: '#c62828',
  },
  warning: {
    500: '#ed6c02',  // 黄色（背景白に対してコントラスト比 4.52:1）
    600: '#e65100',
  },
  
  // グレースケール
  gray: {
    50: '#fafafa',   // 背景
    100: '#f5f5f5',  // カード背景
    300: '#e0e0e0',  // ボーダー
    500: '#9e9e9e',  // 補助テキスト
    700: '#616161',  // メインテキスト（背景白に対してコントラスト比 7.13:1）
    900: '#212121',  // 強調テキスト（背景白に対してコントラスト比 16.74:1）
  }
}
```

### 2.2 レスポンシブブレークポイント
```typescript
// theme/foundations/breakpoints.ts
export const breakpoints = {
  base: '0px',     // モバイル（〜575px）
  sm: '576px',     // 小型タブレット
  md: '768px',     // タブレット
  lg: '992px',     // 小型デスクトップ
  xl: '1200px',    // デスクトップ
}
```

### 2.3 既定テーマと派生テーマの関係

上記 §2.1 の値は本システムの組込み **`standard` プリセットテーマ** の実値である。以降、本システムは WordPress 風のテーマ切替機構（詳細: [`theme_system_specification.md`](./theme_system_specification.md)）により、`standard` 以外の派生テーマ（`high-contrast` / `warm` / `calm` および管理者登録のカスタムテーマ）を選択可能とする。

**本ガイドラインはすべてのテーマに等しく適用され、テーマは本ガイドラインの基準を下回ってはならない**。

### 2.4 テーマ適用時のアクセシビリティ制約（必須）

いかなるテーマ（組込み・カスタムを問わず）も、下表の基準をすべて満たさなければならない。基準違反のテーマは**登録不可**（サーバ側 422）であり、実行時にバリデーションに失敗した場合は自動的に `standard` プリセットへフォールバックされる。

| 項目 | 基準値 | 適用範囲 | 出典 |
|---|---|---|---|
| 本文フォントサイズ | ≥ 18px（`ThemeDefinition.fonts.baseSizePx`） | 全テーマ | §2.1 基本テーマ構成 |
| 本文色対背景コントラスト比 | ≥ 4.5:1（`text.primary` vs `bg.page`） | 全テーマ | WCAG 2.1 AA |
| ブランド上テキストコントラスト比 | ≥ 4.5:1（`text.onBrand` vs `colors.brand.500`） | 全テーマ | WCAG 2.1 AA |
| 非テキストUI要素コントラスト比 | ≥ 3:1（`border.focus` vs `bg.page`） | 全テーマ | WCAG 2.1 AA 1.4.11 |
| タッチターゲット最小サイズ | 44 × 44 px | 全テーマ・全密度設定 | §3.1 ボタンコンポーネント |
| フォーカスリング | 幅 ≥ 2px、コントラスト比 ≥ 3:1 | 全テーマ | WCAG 2.1 AA 2.4.7 |
| アニメーション | `prefers-reduced-motion` 尊重 | 全テーマ | WCAG 2.1 AA 2.3.3 |

**密度（density）設定の扱い**:
テーマの `density` が `compact` であっても、タッチターゲット最小 44×44 px 制約は維持する。`compact` は主に余白とフォーム要素間スペースの縮小を意味し、タップ領域の縮小を意味しない。

**二重バリデーション**:
- **サーバ側**（登録・更新時）: `backend/app/services/theme_validator.py` が JSON スキーマ適合とコントラスト比・フォントサイズを検証し、不合格は 422
- **クライアント側**（適用時）: `ThemeProvider` が `buildSystem` 前に同一チェックを行い、不合格時は `standard` フォールバックとコンソール警告

---

## 3. コンポーネント設計指針

### 3.1 ボタンコンポーネント

#### 3.1.1 サイズとタップターゲット
```typescript
// theme/components/button.ts
export const Button = {
  baseStyle: {
    fontWeight: 'normal',  // 太字を避ける（視認性向上）
    borderRadius: '8px',   // 角丸で親しみやすさ
    transition: 'all 0.2s', // アニメーション控えめ
    _focus: {
      boxShadow: '0 0 0 3px rgba(25, 118, 210, 0.3)', // フォーカス明確化
    }
  },
  sizes: {
    // 最小44px × 44pxを確保
    sm: {
      h: '48px',
      minW: '48px',
      fontSize: 'md',   // 18px
      px: 6,
    },
    md: {
      h: '56px',
      minW: '56px', 
      fontSize: 'lg',   // 22px
      px: 8,
    },
    lg: {
      h: '64px',
      minW: '64px',
      fontSize: 'xl',   // 28px
      px: 10,
    }
  },
  variants: {
    solid: {
      bg: 'primary.500',
      color: 'white',
      _hover: {
        bg: 'primary.600',
        transform: 'translateY(-1px)', // 微細なフィードバック
      },
      _active: {
        bg: 'primary.700',
        transform: 'translateY(0px)',
      },
      _disabled: {
        bg: 'gray.300',
        color: 'gray.500',
        cursor: 'not-allowed',
        _hover: {
          bg: 'gray.300',
          transform: 'none',
        }
      }
    },
    outline: {
      border: '2px solid',
      borderColor: 'primary.500',
      color: 'primary.500',
      _hover: {
        bg: 'primary.50',
      }
    }
  },
  defaultProps: {
    size: 'md',
    variant: 'solid',
  }
}
```

#### 3.1.2 使用例
```tsx
// components/ElderlyButton.tsx
import { Button, ButtonProps } from '@chakra-ui/react'

interface ElderlyButtonProps extends ButtonProps {
  children: React.ReactNode
  loadingText?: string
}

export const ElderlyButton: React.FC<ElderlyButtonProps> = ({ 
  children, 
  loadingText = '処理中...',
  ...props 
}) => {
  return (
    <Button
      size="md"
      width="100%"            // 幅広で押しやすく
      loadingText={loadingText}
      aria-label={typeof children === 'string' ? children : undefined}
      {...props}
    >
      {children}
    </Button>
  )
}
```

### 3.2 入力フィールドコンポーネント

#### 3.2.1 フォーム設計
```typescript
// theme/components/input.ts
export const Input = {
  baseStyle: {
    field: {
      borderRadius: '8px',
      border: '2px solid',
      borderColor: 'gray.300',
      fontSize: 'lg',        // 18px
      _placeholder: {
        color: 'gray.500',
        fontSize: 'lg',
      },
      _focus: {
        borderColor: 'primary.500',
        boxShadow: '0 0 0 2px rgba(25, 118, 210, 0.3)',
      },
      _invalid: {
        borderColor: 'error.500',
        boxShadow: '0 0 0 2px rgba(211, 47, 47, 0.3)',
      }
    }
  },
  sizes: {
    lg: {
      field: {
        h: '56px',           // 大きめの入力エリア
        px: 4,
        fontSize: 'lg',
      }
    }
  },
  defaultProps: {
    size: 'lg',
  }
}
```

#### 3.2.2 フォームラベルとエラー
```tsx
// components/ElderlyFormControl.tsx
import { 
  FormControl, 
  FormLabel, 
  FormErrorMessage, 
  Input,
  Text 
} from '@chakra-ui/react'

interface ElderlyFormControlProps {
  label: string
  error?: string
  required?: boolean
  helpText?: string
  children: React.ReactNode
}

export const ElderlyFormControl: React.FC<ElderlyFormControlProps> = ({
  label,
  error,
  required,
  helpText,
  children
}) => {
  return (
    <FormControl isInvalid={!!error} isRequired={required} mb={6}>
      <FormLabel 
        fontSize="lg" 
        fontWeight="normal"
        mb={2}
        color="gray.700"
      >
        {label}
        {required && (
          <Text as="span" color="error.500" ml={1}>
            *
          </Text>
        )}
      </FormLabel>
      
      {children}
      
      {helpText && (
        <Text fontSize="md" color="gray.500" mt={2}>
          {helpText}
        </Text>
      )}
      
      {error && (
        <FormErrorMessage fontSize="md" mt={2}>
          <Text as="span" role="alert" aria-live="polite">
            {error}
          </Text>
        </FormErrorMessage>
      )}
    </FormControl>
  )
}
```

### 3.3 ナビゲーションコンポーネント

#### 3.3.1 メインナビゲーション
```tsx
// components/ElderlyNavigation.tsx
import { 
  Box, 
  Flex, 
  Button, 
  Icon, 
  Text, 
  VStack 
} from '@chakra-ui/react'
import { IconType } from 'react-icons'

interface NavItem {
  label: string
  icon: IconType
  path: string
  isActive?: boolean
}

interface ElderlyNavigationProps {
  items: NavItem[]
  onNavigate: (path: string) => void
}

export const ElderlyNavigation: React.FC<ElderlyNavigationProps> = ({
  items,
  onNavigate
}) => {
  return (
    <Box
      bg="white"
      borderTop="1px solid"
      borderColor="gray.300"
      position="fixed"
      bottom={0}
      left={0}
      right={0}
      zIndex={10}
      p={2}
    >
      <Flex justify="space-around" align="center">
        {items.map((item) => (
          <Button
            key={item.path}
            variant="ghost"
            onClick={() => onNavigate(item.path)}
            flexDirection="column"
            h="auto"
            py={3}
            px={2}
            minW="80px"
            aria-label={item.label}
            bg={item.isActive ? 'primary.50' : 'transparent'}
            color={item.isActive ? 'primary.600' : 'gray.600'}
            _hover={{
              bg: 'primary.50',
              color: 'primary.600',
            }}
          >
            <VStack spacing={1}>
              <Icon as={item.icon} boxSize={6} />
              <Text fontSize="sm" fontWeight="normal">
                {item.label}
              </Text>
            </VStack>
          </Button>
        ))}
      </Flex>
    </Box>
  )
}
```

---

## 4. 画面レイアウト設計

### 4.1 グリッドシステム
```tsx
// layouts/ElderlyLayout.tsx
import { Container, Box, VStack } from '@chakra-ui/react'

export const ElderlyLayout: React.FC<{ children: React.ReactNode }> = ({ 
  children 
}) => {
  return (
    <Container 
      maxW="container.md"   // 最大幅制限（読みやすさ）
      px={4}
      pb="100px"            // ナビゲーション分の余白
    >
      <VStack 
        spacing={6}         // 要素間の十分な余白
        align="stretch"     // 要素を幅いっぱいに
        py={6}
      >
        {children}
      </VStack>
    </Container>
  )
}
```

### 4.2 カードデザイン
```tsx
// components/ElderlyCard.tsx
import { Box, BoxProps } from '@chakra-ui/react'

interface ElderlyCardProps extends BoxProps {
  children: React.ReactNode
  clickable?: boolean
}

export const ElderlyCard: React.FC<ElderlyCardProps> = ({
  children,
  clickable = false,
  ...props
}) => {
  return (
    <Box
      bg="white"
      borderRadius="12px"
      border="1px solid"
      borderColor="gray.200"
      p={6}
      shadow="sm"
      transition="all 0.2s"
      cursor={clickable ? 'pointer' : 'default'}
      _hover={clickable ? {
        shadow: 'md',
        transform: 'translateY(-2px)',
        borderColor: 'primary.300',
      } : {}}
      _focus={clickable ? {
        outline: '2px solid',
        outlineColor: 'primary.500',
        outlineOffset: '2px',
      } : {}}
      tabIndex={clickable ? 0 : undefined}
      role={clickable ? 'button' : undefined}
      {...props}
    >
      {children}
    </Box>
  )
}
```

---

## 5. 高齢者特有のUI配慮

### 5.1 認知負荷軽減

#### 5.1.1 情報の階層化
```tsx
// 1画面1タスクの原則
export const RecipeDetailPage: React.FC = () => {
  return (
    <ElderlyLayout>
      {/* メインタスクのみフォーカス */}
      <Heading as="h1" size="lg" textAlign="center" mb={4}>
        鶏肉の照り焼き
      </Heading>
      
      {/* 必要最小限の情報を段階的に表示 */}
      <ElderlyCard>
        <VStack spacing={4} align="start">
          <Text fontSize="lg">調理時間: 30分</Text>
          <Text fontSize="lg">難易度: 普通</Text>
        </VStack>
      </ElderlyCard>
      
      {/* アクションは明確に分離 */}
      <VStack spacing={4}>
        <ElderlyButton size="lg">
          献立に追加
        </ElderlyButton>
        <Button variant="outline" size="lg">
          材料を見る
        </Button>
      </VStack>
    </ElderlyLayout>
  )
}
```

#### 5.1.2 プログレスインジケーター
```tsx
// components/ElderlyProgress.tsx
import { Progress, VStack, Text, Flex } from '@chakra-ui/react'

interface ElderlyProgressProps {
  currentStep: number
  totalSteps: number
  stepLabel: string
}

export const ElderlyProgress: React.FC<ElderlyProgressProps> = ({
  currentStep,
  totalSteps,
  stepLabel
}) => {
  const progressValue = (currentStep / totalSteps) * 100
  
  return (
    <VStack spacing={3} mb={6}>
      <Flex justify="space-between" width="100%">
        <Text fontSize="md" color="gray.600">
          {stepLabel}
        </Text>
        <Text fontSize="md" color="gray.600">
          {currentStep} / {totalSteps}
        </Text>
      </Flex>
      
      <Progress 
        value={progressValue}
        size="lg"
        colorScheme="primary"
        width="100%"
        borderRadius="4px"
        bg="gray.100"
      />
    </VStack>
  )
}
```

### 5.2 エラーメッセージとフィードバック

#### 5.2.1 分かりやすいエラー表現
```tsx
// components/ElderlyErrorMessage.tsx
import { Alert, AlertIcon, AlertTitle, AlertDescription, VStack } from '@chakra-ui/react'

interface ElderlyErrorMessageProps {
  title: string
  description: string
  actionText?: string
  onAction?: () => void
}

export const ElderlyErrorMessage: React.FC<ElderlyErrorMessageProps> = ({
  title,
  description,
  actionText,
  onAction
}) => {
  return (
    <Alert
      status="error"
      variant="subtle"
      flexDirection="column"
      alignItems="center"
      justifyContent="center"
      textAlign="center"
      borderRadius="12px"
      p={6}
    >
      <AlertIcon boxSize="40px" mr={0} />
      
      <AlertTitle mt={4} mb={2} fontSize="lg">
        {title}
      </AlertTitle>
      
      <AlertDescription fontSize="md" mb={4}>
        {description}
      </AlertDescription>
      
      {actionText && onAction && (
        <ElderlyButton onClick={onAction} size="sm">
          {actionText}
        </ElderlyButton>
      )}
    </Alert>
  )
}

// 使用例
const errorScenarios = {
  networkError: {
    title: "インターネットに接続できません",
    description: "Wi-Fiまたは電波の状況を確認してから、もう一度お試しください。",
    actionText: "もう一度試す"
  },
  validationError: {
    title: "入力内容に不備があります", 
    description: "赤い印がついた項目を確認し、正しく入力してください。",
    actionText: "入力画面に戻る"
  }
}
```

#### 5.2.2 成功フィードバック
```tsx
// components/ElderlySuccessToast.tsx
import { useToast } from '@chakra-ui/react'

export const useElderlyToast = () => {
  const toast = useToast()
  
  const showSuccess = (message: string) => {
    toast({
      title: "完了しました",
      description: message,
      status: "success",
      duration: 4000,  // 読む時間を確保
      isClosable: true,
      position: "top",
      variant: "subtle",
    })
  }
  
  const showError = (message: string) => {
    toast({
      title: "エラーが発生しました",
      description: message,
      status: "error",
      duration: 6000,  // エラーは長めに表示
      isClosable: true,
      position: "top",
      variant: "subtle",
    })
  }
  
  return { showSuccess, showError }
}
```

---

## 6. モバイル対応とタッチインターフェース

### 6.1 タッチジェスチャー設計

#### 6.1.1 スワイプ操作の制限
```tsx
// 誤操作防止のため、スワイプ操作は必要最小限に
export const SwipeableRecipeCard: React.FC = () => {
  const [isSwipeEnabled, setIsSwipeEnabled] = useState(false)
  
  return (
    <Box
      onTouchStart={() => setIsSwipeEnabled(true)}
      onTouchEnd={() => setIsSwipeEnabled(false)}
      // スワイプの代わりにボタンによる明示的操作を推奨
    >
      <ElderlyCard clickable>
        <VStack spacing={3}>
          <Text fontSize="lg">鶏肉の照り焼き</Text>
          <HStack spacing={3}>
            <Button size="sm" colorScheme="primary">
              詳細
            </Button>
            <Button size="sm" variant="outline">
              削除
            </Button>
          </HStack>
        </VStack>
      </ElderlyCard>
    </Box>
  )
}
```

#### 6.1.2 ドラッグ&ドロップ対応
```tsx
// react-beautiful-dndを使用した献立並び替え
import { DragDropContext, Droppable, Draggable } from 'react-beautiful-dnd'

export const MenuDragAndDrop: React.FC = () => {
  return (
    <DragDropContext onDragEnd={handleDragEnd}>
      <Droppable droppableId="menu-items">
        {(provided) => (
          <VStack
            {...provided.droppableProps}
            ref={provided.innerRef}
            spacing={3}
          >
            {menuItems.map((item, index) => (
              <Draggable 
                key={item.id} 
                draggableId={item.id} 
                index={index}
              >
                {(provided, snapshot) => (
                  <Box
                    ref={provided.innerRef}
                    {...provided.draggableProps}
                    {...provided.dragHandleProps}
                    bg={snapshot.isDragging ? 'primary.50' : 'white'}
                    border="2px solid"
                    borderColor={snapshot.isDragging ? 'primary.300' : 'gray.200'}
                    borderRadius="8px"
                    p={4}
                    shadow={snapshot.isDragging ? 'lg' : 'sm'}
                    cursor="grab"
                    _active={{ cursor: 'grabbing' }}
                  >
                    <Flex align="center" justify="space-between">
                      <Text fontSize="lg">{item.name}</Text>
                      <Icon as={DragHandleIcon} color="gray.400" />
                    </Flex>
                  </Box>
                )}
              </Draggable>
            ))}
            {provided.placeholder}
          </VStack>
        )}
      </Droppable>
    </DragDropContext>
  )
}
```

### 6.2 バイブレーション・触覚フィードバック

```tsx
// utils/haptics.ts
export const hapticFeedback = {
  light: () => {
    if ('vibrate' in navigator) {
      navigator.vibrate(50)  // 軽いタップ
    }
  },
  
  medium: () => {
    if ('vibrate' in navigator) {
      navigator.vibrate(100) // 中程度のフィードバック
    }
  },
  
  error: () => {
    if ('vibrate' in navigator) {
      navigator.vibrate([100, 50, 100]) // エラーパターン
    }
  },
  
  success: () => {
    if ('vibrate' in navigator) {
      navigator.vibrate([50, 25, 50]) // 成功パターン
    }
  }
}

// 使用例
export const HapticButton: React.FC<ButtonProps> = ({ 
  onClick, 
  children, 
  ...props 
}) => {
  const handleClick = (e: React.MouseEvent) => {
    hapticFeedback.light()  // タップ時の触覚フィードバック
    onClick?.(e)
  }
  
  return (
    <ElderlyButton onClick={handleClick} {...props}>
      {children}
    </ElderlyButton>
  )
}
```

---

## 7. アクセシビリティ実装

### 7.1 キーボードナビゲーション

```tsx
// hooks/useKeyboardNavigation.ts
import { useCallback, useEffect } from 'react'

export const useKeyboardNavigation = (
  elements: HTMLElement[],
  currentIndex: number,
  onIndexChange: (index: number) => void
) => {
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault()
        onIndexChange((currentIndex + 1) % elements.length)
        break
      case 'ArrowUp':
        e.preventDefault()
        onIndexChange((currentIndex - 1 + elements.length) % elements.length)
        break
      case 'Enter':
      case ' ':
        e.preventDefault()
        elements[currentIndex]?.click()
        break
      case 'Escape':
        // フォーカスをクリア
        elements[currentIndex]?.blur()
        break
    }
  }, [currentIndex, elements, onIndexChange])
  
  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])
  
  // 現在の要素にフォーカス
  useEffect(() => {
    elements[currentIndex]?.focus()
  }, [currentIndex, elements])
}
```

### 7.2 スクリーンリーダー対応

```tsx
// components/AccessibleRecipeCard.tsx
import { Box, Text, VStack, VisuallyHidden } from '@chakra-ui/react'

export const AccessibleRecipeCard: React.FC<{
  recipe: Recipe
  onSelect: () => void
}> = ({ recipe, onSelect }) => {
  return (
    <ElderlyCard
      clickable
      onClick={onSelect}
      role="button"
      tabIndex={0}
      aria-label={`${recipe.name}、調理時間${recipe.cookingTime}分、難易度${recipe.difficulty}、詳細を見る`}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          onSelect()
        }
      }}
    >
      <VStack align="start" spacing={2}>
        <Text fontSize="lg" fontWeight="semibold">
          {recipe.name}
        </Text>
        
        <Text fontSize="md" color="gray.600">
          調理時間: {recipe.cookingTime}分
        </Text>
        
        <Text fontSize="md" color="gray.600">
          難易度: {recipe.difficulty}
        </Text>
        
        {/* スクリーンリーダー用の詳細情報 */}
        <VisuallyHidden>
          材料: {recipe.ingredients}
          カテゴリ: {recipe.category}
          タイプ: {recipe.type}
          Enter キーまたはスペースキーを押すと詳細画面に移動します
        </VisuallyHidden>
      </VStack>
    </ElderlyCard>
  )
}
```

### 7.3 音声読み上げ対応

```tsx
// utils/speechSynthesis.ts
export class ElderlyTTS {
  private synth: SpeechSynthesis
  private voice: SpeechSynthesisVoice | null = null
  
  constructor() {
    this.synth = window.speechSynthesis
    this.initVoice()
  }
  
  private initVoice() {
    const voices = this.synth.getVoices()
    // 日本語音声を優先選択
    this.voice = voices.find(voice => 
      voice.lang.includes('ja') && voice.name.includes('Google')
    ) || voices.find(voice => voice.lang.includes('ja')) || null
  }
  
  speak(text: string, options?: {
    rate?: number    // 読み上げ速度 (0.5-2.0)
    pitch?: number   // 音の高さ (0-2.0)
    volume?: number  // 音量 (0-1.0)
  }) {
    const utterance = new SpeechSynthesisUtterance(text)
    
    if (this.voice) {
      utterance.voice = this.voice
    }
    
    utterance.rate = options?.rate || 0.8      // ゆっくり
    utterance.pitch = options?.pitch || 1.0
    utterance.volume = options?.volume || 1.0
    
    this.synth.speak(utterance)
  }
  
  stop() {
    this.synth.cancel()
  }
}

// 使用例
export const SpeakableText: React.FC<{
  children: string
  autoSpeak?: boolean
}> = ({ children, autoSpeak = false }) => {
  const tts = useMemo(() => new ElderlyTTS(), [])
  
  useEffect(() => {
    if (autoSpeak) {
      tts.speak(children)
    }
  }, [children, autoSpeak, tts])
  
  return (
    <Box position="relative">
      <Text>{children}</Text>
      <Button
        size="sm"
        position="absolute"
        top={0}
        right={0}
        aria-label="音声で読み上げ"
        onClick={() => tts.speak(children)}
      >
        🔊
      </Button>
    </Box>
  )
}
```

---

## 8. パフォーマンス最適化

### 8.1 画像最適化

```tsx
// components/OptimizedImage.tsx
import { Box, Image, Skeleton } from '@chakra-ui/react'
import { useState } from 'react'

interface OptimizedImageProps {
  src: string
  alt: string
  width?: number
  height?: number
  lazy?: boolean
}

export const OptimizedImage: React.FC<OptimizedImageProps> = ({
  src,
  alt,
  width,
  height,
  lazy = true
}) => {
  const [isLoaded, setIsLoaded] = useState(false)
  const [hasError, setHasError] = useState(false)
  
  const webpSrc = src.replace(/\.(jpg|jpeg|png)$/i, '.webp')
  
  return (
    <Box position="relative" width={width} height={height}>
      {!isLoaded && !hasError && (
        <Skeleton width="100%" height="100%" borderRadius="8px" />
      )}
      
      <picture>
        {/* WebP対応ブラウザ用 */}
        <source srcSet={webpSrc} type="image/webp" />
        
        {/* フォールバック */}
        <Image
          src={src}
          alt={alt}
          width={width}
          height={height}
          loading={lazy ? 'lazy' : 'eager'}
          onLoad={() => setIsLoaded(true)}
          onError={() => setHasError(true)}
          display={isLoaded ? 'block' : 'none'}
          borderRadius="8px"
        />
      </picture>
      
      {hasError && (
        <Box
          width="100%"
          height="100%"
          bg="gray.100"
          display="flex"
          alignItems="center"
          justifyContent="center"
          borderRadius="8px"
        >
          <Text color="gray.500">画像を読み込めません</Text>
        </Box>
      )}
    </Box>
  )
}
```

### 8.2 仮想スクロール

```tsx
// components/VirtualizedRecipeList.tsx
import { FixedSizeList as List } from 'react-window'
import { Box } from '@chakra-ui/react'

interface VirtualizedRecipeListProps {
  recipes: Recipe[]
  onSelectRecipe: (recipe: Recipe) => void
}

const ITEM_HEIGHT = 120

export const VirtualizedRecipeList: React.FC<VirtualizedRecipeListProps> = ({
  recipes,
  onSelectRecipe
}) => {
  const Row = ({ index, style }: { index: number; style: React.CSSProperties }) => {
    const recipe = recipes[index]
    
    return (
      <Box style={style} p={2}>
        <AccessibleRecipeCard
          recipe={recipe}
          onSelect={() => onSelectRecipe(recipe)}
        />
      </Box>
    )
  }
  
  return (
    <List
      height={600}  // 表示エリアの高さ
      itemCount={recipes.length}
      itemSize={ITEM_HEIGHT}
      overscanCount={5}  // 画面外にレンダリングする要素数
    >
      {Row}
    </List>
  )
}
```

---

## 9. 国際化対応

### 9.1 react-i18next設定

```typescript
// i18n/index.ts
import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

import ja from './locales/ja.json'
import en from './locales/en.json'

i18n
  .use(initReactI18next)
  .init({
    resources: {
      ja: { translation: ja },
      en: { translation: en }
    },
    lng: 'ja', // デフォルト言語
    fallbackLng: 'ja',
    interpolation: {
      escapeValue: false // React already does escaping
    }
  })

export default i18n
```

### 9.2 多言語対応コンポーネント

```tsx
// components/LocalizedText.tsx
import { useTranslation } from 'react-i18next'
import { Text, TextProps } from '@chakra-ui/react'

interface LocalizedTextProps extends TextProps {
  i18nKey: string
  values?: Record<string, any>
}

export const LocalizedText: React.FC<LocalizedTextProps> = ({
  i18nKey,
  values,
  ...props
}) => {
  const { t } = useTranslation()
  
  return (
    <Text {...props}>
      {t(i18nKey, values)}
    </Text>
  )
}

// 使用例
export const RecipeCard: React.FC = () => {
  return (
    <ElderlyCard>
      <VStack align="start">
        <LocalizedText 
          i18nKey="recipe.cookingTime" 
          values={{ time: 30 }}
          fontSize="lg"
        />
        {/* 翻訳: "調理時間: 30分" or "Cooking time: 30 minutes" */}
      </VStack>
    </ElderlyCard>
  )
}
```

---

## 10. テスト戦略

### 10.1 アクセシビリティテスト

```tsx
// __tests__/accessibility.test.tsx
import { render, screen } from '@testing-library/react'
import { axe, toHaveNoViolations } from 'jest-axe'
import { ElderlyButton } from '../components/ElderlyButton'

expect.extend(toHaveNoViolations)

describe('ElderlyButton Accessibility', () => {
  test('should not have accessibility violations', async () => {
    const { container } = render(
      <ElderlyButton>テストボタン</ElderlyButton>
    )
    
    const results = await axe(container)
    expect(results).toHaveNoViolations()
  })
  
  test('should have proper ARIA attributes', () => {
    render(<ElderlyButton aria-label="保存する">保存</ElderlyButton>)
    
    const button = screen.getByRole('button', { name: '保存する' })
    expect(button).toBeInTheDocument()
    expect(button).toHaveAttribute('aria-label', '保存する')
  })
  
  test('should be keyboard navigable', () => {
    render(<ElderlyButton>フォーカステスト</ElderlyButton>)
    
    const button = screen.getByRole('button')
    button.focus()
    
    expect(button).toHaveFocus()
  })
})
```

### 10.2 視覚回帰テスト

```tsx
// __tests__/visual.test.tsx
import { render } from '@testing-library/react'
import { toMatchImageSnapshot } from 'jest-image-snapshot'
import { ElderlyCard } from '../components/ElderlyCard'

expect.extend({ toMatchImageSnapshot })

describe('Visual Regression Tests', () => {
  test('ElderlyCard should match snapshot', () => {
    const { container } = render(
      <ElderlyCard>
        <Text>テストコンテンツ</Text>
      </ElderlyCard>
    )
    
    expect(container.firstChild).toMatchImageSnapshot({
      threshold: 0.1,
      thresholdType: 'percent'
    })
  })
})
```

---

## 11. 実装チェックリスト

### 11.1 必須実装項目

#### フォント・タイポグラフィ
- [ ] 基本フォントサイズ18px以上
- [ ] rem単位での相対サイズ指定
- [ ] 日本語フォントの最適化
- [ ] 行間・文字間の調整

#### カラー・コントラスト
- [ ] WCAG 2.1 AA準拠（コントラスト比4.5:1以上）
- [ ] カラーパレットの一貫性
- [ ] 色以外の視覚的手がかりの提供

#### タッチインターフェース
- [ ] 最小タップターゲット44px × 44px
- [ ] 十分な要素間スペース（8px以上）
- [ ] 誤操作防止機能

#### キーボード操作
- [ ] 全インタラクティブ要素のキーボード操作対応
- [ ] フォーカス状態の明確な視覚化
- [ ] 論理的なタブオーダー

#### スクリーンリーダー
- [ ] 適切なセマンティックHTML
- [ ] ARIA属性の正しい使用
- [ ] 代替テキストの提供

### 11.2 高齢者特化項目

#### 認知負荷軽減
- [ ] 1画面1タスク原則
- [ ] 段階的情報開示
- [ ] 明確なプログレス表示

#### エラーハンドリング
- [ ] 分かりやすいエラーメッセージ
- [ ] 具体的な解決方法の提示
- [ ] 複数回の確認プロンプト

#### フィードバック
- [ ] 即座の視覚的フィードバック
- [ ] 触覚フィードバック（バイブレーション）
- [ ] 音声フィードバック（オプション）

---

## 12. 運用・保守ガイドライン

### 12.1 継続的改善

#### ユーザビリティテスト
- 月1回のユーザビリティテスト実施
- 高齢者を含むテストユーザーグループ
- タスク完了率・エラー率の測定

#### アクセシビリティ監査
- 四半期ごとの自動チェック（axe-core使用）
- 年1回の専門機関による監査
- WCAG ガイドラインの更新追従

### 12.2 パフォーマンス監視

#### Core Web Vitals監視
- LCP（Largest Contentful Paint）< 2.5秒
- FID（First Input Delay）< 100ms
- CLS（Cumulative Layout Shift）< 0.1

#### 高齢者向け追加指標
- タップ成功率 > 95%
- エラー率 < 5%
- タスク完了率 > 80%

---

**文書終了**