import { useState, useMemo } from 'react'
import {
  Box,
  Heading,
  Text,
  VStack,
  HStack,
  Input,
  Badge,
  AccordionRoot,
  AccordionItem,
  AccordionItemTrigger,
  AccordionItemContent,
  AccordionItemBody,
} from '@chakra-ui/react'
import PageHeader from '@/components/ui/PageHeader'
import { useAuthStore } from '@/stores/auth'

// ── SVG icon paths (reusing nav icons where applicable) ─────────────
const ICONS = {
  info: 'M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
  login: 'M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1',
  senior: 'M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z',
  helper: 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z',
  careManager: 'M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z',
  admin: 'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z M15 12a3 3 0 11-6 0 3 3 0 016 0z',
  faq: 'M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
  contact: 'M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z',
  recipe: 'M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253',
  menu: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01',
  shopping: 'M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 100 4 2 2 0 000-4z',
  pantry: 'M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4',
  message: 'M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z',
  task: 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z',
  users: 'M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z',
  assign: 'M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4',
}

function SectionIcon({ d, color = '#0369A1' }: { d: string; color?: string }) {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d={d} />
    </svg>
  )
}

// ── Chevron icon for accordion ──────────────────────────────────────
function ChevronIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M6 9l6 6 6-6" />
    </svg>
  )
}

// ── Step list component ─────────────────────────────────────────────
function StepList({ steps }: { steps: string[] }) {
  return (
    <Box as="ol" pl={6} listStyleType="decimal">
      {steps.map((step, i) => (
        <Box as="li" key={i} mb={2} fontSize="lg" color="text.primary" lineHeight="1.8">
          {step}
        </Box>
      ))}
    </Box>
  )
}

// ── Sub-section component ───────────────────────────────────────────
function SubSection({ title, icon, children }: { title: string; icon?: string; children: React.ReactNode }) {
  return (
    <Box mb={6}>
      <HStack gap={2} mb={3}>
        {icon && <SectionIcon d={icon} color="#0EA5E9" />}
        <Heading size="md" color="text.primary" fontWeight="semibold">
          {title}
        </Heading>
      </HStack>
      <Box pl={icon ? 8 : 0}>{children}</Box>
    </Box>
  )
}

// ── Help section data ───────────────────────────────────────────────
interface HelpSection {
  id: string
  title: string
  icon: string
  roles: string[] // which roles this section is most relevant to
  content: React.ReactNode
  keywords: string[]
}

function useHelpSections(): HelpSection[] {
  return useMemo(() => [
    {
      id: 'overview',
      title: 'はじめに（システム概要）',
      icon: ICONS.info,
      roles: ['senior', 'helper', 'care_manager', 'system_admin'],
      keywords: ['システム', '概要', 'はじめに', '機能', 'ブラウザ', 'デバイス', '対応'],
      content: (
        <VStack align="stretch" gap={4}>
          <SubSection title="ホームヘルパー管理システムとは">
            <Text fontSize="lg" color="text.primary" lineHeight="1.8">
              ホームヘルパー管理システムは、在宅介護に関わる<strong>利用者（高齢者）</strong>、
              <strong>ホームヘルパー</strong>、<strong>ケアマネージャー</strong>をつなぐ総合管理システムです。
              日々の食事管理、作業管理、買い物依頼、メッセージのやり取りなど、
              介護サービスに必要な情報共有をスムーズに行えます。
            </Text>
          </SubSection>
          <SubSection title="利用できる機能">
            <Box as="ul" pl={6} listStyleType="disc">
              <Box as="li" mb={2} fontSize="lg" color="text.primary" lineHeight="1.8">
                <strong>レシピ管理</strong> — レシピの登録・検索・管理
              </Box>
              <Box as="li" mb={2} fontSize="lg" color="text.primary" lineHeight="1.8">
                <strong>献立管理</strong> — 週間献立の作成・管理
              </Box>
              <Box as="li" mb={2} fontSize="lg" color="text.primary" lineHeight="1.8">
                <strong>作業管理</strong> — 日々の作業スケジュール確認・完了報告
              </Box>
              <Box as="li" mb={2} fontSize="lg" color="text.primary" lineHeight="1.8">
                <strong>メッセージ</strong> — ヘルパーと利用者のやり取り
              </Box>
              <Box as="li" mb={2} fontSize="lg" color="text.primary" lineHeight="1.8">
                <strong>買い物管理</strong> — 買い物依頼の作成・状況管理
              </Box>
              <Box as="li" mb={2} fontSize="lg" color="text.primary" lineHeight="1.8">
                <strong>パントリー</strong> — 食材在庫の管理
              </Box>
            </Box>
          </SubSection>
          <SubSection title="対応ブラウザ・デバイス">
            <Text fontSize="lg" color="text.primary" lineHeight="1.8" mb={2}>
              以下のブラウザ・デバイスに対応しています：
            </Text>
            <Box as="ul" pl={6} listStyleType="disc">
              <Box as="li" mb={1} fontSize="lg" color="text.primary">Google Chrome（バージョン90以降）</Box>
              <Box as="li" mb={1} fontSize="lg" color="text.primary">Safari（バージョン14以降）</Box>
              <Box as="li" mb={1} fontSize="lg" color="text.primary">Firefox（バージョン88以降）</Box>
              <Box as="li" mb={1} fontSize="lg" color="text.primary">Microsoft Edge（バージョン90以降）</Box>
              <Box as="li" mb={1} fontSize="lg" color="text.primary">iPhone / iPad（iOS 14以降）</Box>
              <Box as="li" mb={1} fontSize="lg" color="text.primary">Android スマートフォン / タブレット（Android 10以降）</Box>
            </Box>
          </SubSection>
        </VStack>
      ),
    },
    {
      id: 'login',
      title: 'ログイン・アカウント',
      icon: ICONS.login,
      roles: ['senior', 'helper', 'care_manager', 'system_admin'],
      keywords: ['ログイン', 'パスワード', 'QRコード', 'プロフィール', 'ログアウト', 'アカウント'],
      content: (
        <VStack align="stretch" gap={4}>
          <SubSection title="パスワードでログインする">
            <StepList steps={[
              'ログイン画面を開きます。',
              '「メールアドレス」欄にメールアドレスを入力します。',
              '「パスワード」欄にパスワードを入力します。',
              '「ログイン」ボタンを押します。',
              'ダッシュボード画面が表示されたら、ログイン完了です。',
            ]} />
          </SubSection>
          <SubSection title="QRコードでログインする（高齢者向け）">
            <Text fontSize="lg" color="text.primary" lineHeight="1.8" mb={3}>
              パスワード入力が難しい場合は、QRコードでのログインが便利です。
            </Text>
            <StepList steps={[
              'ログイン画面で「QRコードでログイン」タブを選びます。',
              'ヘルパーやケアマネージャーから渡されたQRコードを用意します。',
              'カメラでQRコードを読み取るか、コードを入力します。',
              '自動的にログインが完了します。',
            ]} />
          </SubSection>
          <SubSection title="プロフィールを確認・編集する">
            <StepList steps={[
              '画面上部のヘッダーにある自分の名前をクリックします。',
              'プロフィール画面が開きます。',
              '「編集」ボタンを押すと、名前や連絡先を変更できます。',
              '変更後、「保存」ボタンを押して完了です。',
            ]} />
          </SubSection>
          <SubSection title="パスワードを変更する">
            <StepList steps={[
              'プロフィール画面を開きます。',
              '「パスワード変更」セクションを開きます。',
              '現在のパスワードを入力します。',
              '新しいパスワードを2回入力します。',
              '「変更」ボタンを押して完了です。',
            ]} />
            <Box mt={3} p={4} bg="warn.50" borderRadius="lg" borderLeft="4px solid" borderColor="warn.500">
              <Text fontSize="lg" color="text.primary" lineHeight="1.8">
                パスワードは8文字以上で、英字と数字を含めてください。
              </Text>
            </Box>
          </SubSection>
          <SubSection title="ログアウトする">
            <Text fontSize="lg" color="text.primary" lineHeight="1.8">
              画面右上の「ログアウト」ボタンを押すと、安全にログアウトできます。
              共有のパソコンを使っている場合は、必ずログアウトしてください。
            </Text>
          </SubSection>
        </VStack>
      ),
    },
    {
      id: 'senior',
      title: '利用者（高齢者）向けガイド',
      icon: ICONS.senior,
      roles: ['senior'],
      keywords: ['利用者', '高齢者', 'シニア', 'レシピ', '献立', '買い物', 'パントリー', 'メッセージ'],
      content: (
        <VStack align="stretch" gap={4}>
          <SubSection title="レシピ管理" icon={ICONS.recipe}>
            <Text fontSize="lg" color="text.primary" lineHeight="1.8" mb={3}>
              お気に入りのレシピを登録・管理できます。ヘルパーさんが調理する際の参考になります。
            </Text>
            <Heading size="sm" color="text.secondary" mb={2} fontWeight="semibold">レシピを登録する</Heading>
            <StepList steps={[
              'ナビゲーションの「レシピ」を押します。',
              '右上の「レシピ追加」ボタンを押します。',
              'レシピ名、カテゴリ（和食・洋食・中華など）、種類（主菜・副菜・汁物など）を選びます。',
              '調理時間と難易度を設定します。',
              '材料を入力します（名前、分量、単位）。',
              '作り方を順番に入力します。',
              'メモや参考URLがあれば入力します。',
              '「保存」ボタンを押して完了です。',
            ]} />
            <Heading size="sm" color="text.secondary" mb={2} mt={4} fontWeight="semibold">レシピを検索・フィルタリングする</Heading>
            <Text fontSize="lg" color="text.primary" lineHeight="1.8">
              レシピ一覧画面で、キーワード検索のほか、カテゴリ（和食・洋食など）、
              種類（主菜・副菜など）、難易度（簡単・普通・難しい）でフィルタリングできます。
            </Text>
            <Heading size="sm" color="text.secondary" mb={2} mt={4} fontWeight="semibold">レシピを編集・削除する</Heading>
            <StepList steps={[
              'レシピ一覧からレシピをクリックして詳細を開きます。',
              '「編集」ボタンで内容を変更できます。',
              '「削除」ボタンでレシピを削除できます（確認画面が表示されます）。',
            ]} />
          </SubSection>

          <SubSection title="献立管理" icon={ICONS.menu}>
            <Text fontSize="lg" color="text.primary" lineHeight="1.8" mb={3}>
              1週間分の朝食と夕食の献立を計画できます。登録済みのレシピから選んで設定します。
            </Text>
            <Heading size="sm" color="text.secondary" mb={2} fontWeight="semibold">週間献立を作成する</Heading>
            <StepList steps={[
              'ナビゲーションの「献立」を押します。',
              '各曜日の「朝食」「夕食」欄にレシピを設定します。',
              'レシピ選択画面から好きなレシピを選びます。',
              '設定した献立は自動的に保存されます。',
            ]} />
            <Text fontSize="lg" color="text.primary" lineHeight="1.8" mt={3}>
              献立画面では、登録したレシピの数、平均調理時間、料理カテゴリの分布などの
              分析情報も確認できます。栄養バランスの参考にしてください。
            </Text>
          </SubSection>

          <SubSection title="買い物管理" icon={ICONS.shopping}>
            <Text fontSize="lg" color="text.primary" lineHeight="1.8" mb={3}>
              ヘルパーさんに買い物を依頼できます。献立から自動で買い物リストを作ることもできます。
            </Text>
            <Heading size="sm" color="text.secondary" mb={2} fontWeight="semibold">買い物リストを自動生成する</Heading>
            <StepList steps={[
              '献立画面で「買い物リスト生成」ボタンを押します。',
              '週間献立に必要な材料が自動でリストアップされます。',
              'パントリー（在庫）にある材料は自動で除外されます。',
              '必要に応じてリストを編集し、ヘルパーさんに依頼します。',
            ]} />
            <Heading size="sm" color="text.secondary" mb={2} mt={4} fontWeight="semibold">買い物の状況を確認する</Heading>
            <Text fontSize="lg" color="text.primary" lineHeight="1.8">
              買い物管理画面で、各依頼の状況が確認できます。
              「依頼中」「購入済み」などのステータスで、進捗がわかります。
            </Text>
          </SubSection>

          <SubSection title="パントリー（食材在庫）" icon={ICONS.pantry}>
            <Text fontSize="lg" color="text.primary" lineHeight="1.8" mb={3}>
              ご自宅にある食材の在庫を管理できます。買い物リストの自動生成に活用されます。
            </Text>
            <StepList steps={[
              'ナビゲーションの「パントリー」を押します。',
              '「追加」ボタンで食材を登録します。',
              '食材名、数量、単位を入力します。',
              '在庫がなくなったら数量を0にするか削除します。',
            ]} />
          </SubSection>

          <SubSection title="メッセージ" icon={ICONS.message}>
            <Text fontSize="lg" color="text.primary" lineHeight="1.8" mb={3}>
              担当のヘルパーさんとメッセージでやり取りできます。
            </Text>
            <StepList steps={[
              'ナビゲーションの「メッセージ」を押します。',
              'メッセージの入力欄にテキストを入力します。',
              '「送信」ボタンを押してメッセージを送ります。',
              '相手からの返信は画面に自動的に表示されます。',
            ]} />
            <Box mt={3} p={4} bg="brand.50" borderRadius="lg" borderLeft="4px solid" borderColor="brand.500">
              <Text fontSize="lg" color="text.primary" lineHeight="1.8">
                未読のメッセージがある場合、メッセージ画面に通知が表示されます。
              </Text>
            </Box>
          </SubSection>
        </VStack>
      ),
    },
    {
      id: 'helper',
      title: 'ヘルパー向けガイド',
      icon: ICONS.helper,
      roles: ['helper'],
      keywords: ['ヘルパー', '作業', 'ダッシュボード', '調理', '定期', '特別依頼', '買い物', '作業報告', '日報'],
      content: (
        <VStack align="stretch" gap={4}>
          <SubSection title="ダッシュボード（ホーム画面）">
            <Text fontSize="lg" color="text.primary" lineHeight="1.8">
              ログイン後のダッシュボードでは、本日の担当利用者、スケジュール、
              各機能へのショートカットが表示されます。ここから各作業にアクセスできます。
            </Text>
          </SubSection>

          <SubSection title="作業管理" icon={ICONS.task}>
            <Text fontSize="lg" color="text.primary" lineHeight="1.8" mb={3}>
              本日の作業一覧を確認し、完了状況を管理します。
            </Text>
            <StepList steps={[
              'ナビゲーションの「作業管理」を押します。',
              '本日の作業が一覧で表示されます。',
              '各作業の詳細を確認し、内容を把握します。',
              '作業が完了したら、チェックボックスを押して完了にします。',
              '進捗バーで全体の進み具合を確認できます。',
            ]} />
          </SubSection>

          <SubSection title="調理作業" icon={ICONS.recipe}>
            <Text fontSize="lg" color="text.primary" lineHeight="1.8" mb={3}>
              利用者が登録したレシピに従って調理します。
            </Text>
            <StepList steps={[
              '作業管理画面から調理の作業を開きます。',
              'レシピの材料一覧と手順が表示されます。',
              '複数の料理がある場合は、それぞれの手順を確認できます。',
              '調理時間の目安を参考に、効率よく進めましょう。',
              '完了したら作業を「完了」にします。',
            ]} />
          </SubSection>

          <SubSection title="定期作業（洗濯・掃除など）">
            <Text fontSize="lg" color="text.primary" lineHeight="1.8" mb={3}>
              定期的に行う家事作業のスケジュールと内容を管理します。
            </Text>
            <Text fontSize="lg" color="text.primary" lineHeight="1.8">
              作業管理画面に、予定されている定期作業が表示されます。
              洗濯、掃除、整理整頓など、各作業の内容と推定時間を確認して進めてください。
              完了後はチェックを付けて報告します。
            </Text>
          </SubSection>

          <SubSection title="特別依頼の対応">
            <Text fontSize="lg" color="text.primary" lineHeight="1.8" mb={3}>
              利用者からの特別な依頼は、優先度（高・中・低）で分類されています。
            </Text>
            <Box as="ul" pl={6} listStyleType="disc">
              <Box as="li" mb={2} fontSize="lg" color="text.primary" lineHeight="1.8">
                <Badge bg="danger.100" color="danger.700" mr={2}>高</Badge>
                至急対応が必要な依頼です。最優先で対応してください。
              </Box>
              <Box as="li" mb={2} fontSize="lg" color="text.primary" lineHeight="1.8">
                <Badge bg="warn.100" color="warn.700" mr={2}>中</Badge>
                当日中に対応が必要な依頼です。
              </Box>
              <Box as="li" mb={2} fontSize="lg" color="text.primary" lineHeight="1.8">
                <Badge bg="success.100" color="success.700" mr={2}>低</Badge>
                時間に余裕がある依頼です。他の作業の合間に対応してください。
              </Box>
            </Box>
          </SubSection>

          <SubSection title="買い物対応" icon={ICONS.shopping}>
            <StepList steps={[
              '買い物管理画面で利用者からの依頼一覧を確認します。',
              '依頼された商品名、数量、備考を確認します。',
              '買い物が完了したら、各商品を「購入済み」にします。',
              '必要に応じて購入メモ（代替品の情報など）を記入します。',
            ]} />
          </SubSection>

          <SubSection title="メッセージ" icon={ICONS.message}>
            <Text fontSize="lg" color="text.primary" lineHeight="1.8">
              利用者とメッセージでやり取りできます。作業に関する確認や報告に活用してください。
              緊急時の連絡にもご利用いただけます。操作方法は利用者ガイドと同じです。
            </Text>
          </SubSection>

          <SubSection title="作業報告（日報）">
            <Text fontSize="lg" color="text.primary" lineHeight="1.8" mb={3}>
              1日の作業が終わったら、作業報告を作成します。
            </Text>
            <StepList steps={[
              '作業管理画面で全ての作業完了を確認します。',
              '「作業報告」セクションを開きます。',
              '本日の作業内容のまとめを記入します。',
              '次回のヘルパーへの申し送り事項があれば記入します。',
              '「報告を送信」ボタンを押して完了です。',
            ]} />
            <Box mt={3} p={4} bg="warn.50" borderRadius="lg" borderLeft="4px solid" borderColor="warn.500">
              <Text fontSize="lg" color="text.primary" lineHeight="1.8">
                申し送り事項は、次回担当するヘルパーに共有されます。
                利用者の体調変化や特記事項があれば、必ず記録してください。
              </Text>
            </Box>
          </SubSection>
        </VStack>
      ),
    },
    {
      id: 'care_manager',
      title: 'ケアマネージャー向けガイド',
      icon: ICONS.careManager,
      roles: ['care_manager'],
      keywords: ['ケアマネ', 'ケアマネージャー', '担当', 'モニタリング', 'CSV', 'エクスポート', '進捗'],
      content: (
        <VStack align="stretch" gap={4}>
          <SubSection title="担当利用者・ヘルパーの確認">
            <Text fontSize="lg" color="text.primary" lineHeight="1.8" mb={3}>
              ご自身が担当する利用者とヘルパーの一覧を確認できます。
            </Text>
            <StepList steps={[
              'ダッシュボードに担当利用者の一覧が表示されます。',
              '各利用者の名前をクリックすると、詳細情報を確認できます。',
              '担当ヘルパーの情報も合わせて確認できます。',
            ]} />
          </SubSection>

          <SubSection title="作業完了状況のモニタリング">
            <Text fontSize="lg" color="text.primary" lineHeight="1.8" mb={3}>
              担当する利用者に対する介護サービスの実施状況を確認できます。
            </Text>
            <Text fontSize="lg" color="text.primary" lineHeight="1.8">
              作業管理画面では、各利用者へのサービス提供状況、作業完了率、
              ヘルパーの訪問記録などを確認できます。
              問題がある場合は、早期に対応を検討してください。
            </Text>
          </SubSection>

          <SubSection title="CSVデータエクスポート">
            <Text fontSize="lg" color="text.primary" lineHeight="1.8" mb={3}>
              担当利用者のデータをCSV形式でエクスポートできます。報告書作成に活用してください。
            </Text>
            <StepList steps={[
              'エクスポートしたいデータの画面を開きます。',
              '「CSVエクスポート」ボタンを押します。',
              '期間やフィルタを指定します。',
              'ダウンロードが自動的に開始されます。',
            ]} />
            <Box mt={3} p={4} bg="brand.50" borderRadius="lg" borderLeft="4px solid" borderColor="brand.500">
              <Text fontSize="lg" color="text.primary" lineHeight="1.8">
                エクスポートできるのは、ご自身が担当する利用者のデータのみです。
              </Text>
            </Box>
          </SubSection>
        </VStack>
      ),
    },
    {
      id: 'admin',
      title: '管理者向けガイド',
      icon: ICONS.admin,
      roles: ['system_admin'],
      keywords: ['管理者', 'アドミン', 'ユーザー管理', 'アサイン', 'アカウント', '統計'],
      content: (
        <VStack align="stretch" gap={4}>
          <SubSection title="ユーザー管理" icon={ICONS.users}>
            <Text fontSize="lg" color="text.primary" lineHeight="1.8" mb={3}>
              システムに登録されているユーザーのアカウントを管理します。
            </Text>
            <Heading size="sm" color="text.secondary" mb={2} fontWeight="semibold">新規ユーザーを作成する</Heading>
            <StepList steps={[
              'ナビゲーションの「ユーザー管理」を押します。',
              '「ユーザー追加」ボタンを押します。',
              '氏名、メールアドレス、パスワードを入力します。',
              'ロール（利用者・ヘルパー・ケアマネージャー）を選択します。',
              '「作成」ボタンを押して完了です。',
            ]} />
            <Heading size="sm" color="text.secondary" mb={2} mt={4} fontWeight="semibold">ユーザーを編集・無効化する</Heading>
            <StepList steps={[
              'ユーザー一覧から対象のユーザーを選びます。',
              '「編集」ボタンで名前、メールアドレス、ロールを変更できます。',
              'パスワードリセットが必要な場合は「パスワードリセット」ボタンを使います。',
              'アカウントを無効にする場合は「無効化」ボタンを押します。',
            ]} />
          </SubSection>

          <SubSection title="アサイン管理" icon={ICONS.assign}>
            <Text fontSize="lg" color="text.primary" lineHeight="1.8" mb={3}>
              ヘルパーと利用者の紐付け（アサインメント）を管理します。
            </Text>
            <Heading size="sm" color="text.secondary" mb={2} fontWeight="semibold">新規アサインを作成する</Heading>
            <StepList steps={[
              'ナビゲーションの「アサイン管理」を押します。',
              '「新規アサイン」ボタンを押します。',
              '利用者とヘルパーを選択します。',
              '訪問スケジュール（曜日・時間帯）を設定します。',
              '「作成」ボタンを押して完了です。',
            ]} />
            <Text fontSize="lg" color="text.primary" lineHeight="1.8" mt={3}>
              アサインの変更や終了も、アサイン管理画面から操作できます。
            </Text>
          </SubSection>

          <SubSection title="ダッシュボード（統計情報）">
            <Text fontSize="lg" color="text.primary" lineHeight="1.8">
              管理ダッシュボードでは、以下の統計情報を確認できます：
            </Text>
            <Box as="ul" pl={6} listStyleType="disc" mt={2}>
              <Box as="li" mb={2} fontSize="lg" color="text.primary" lineHeight="1.8">
                ロール別ユーザー数（利用者・ヘルパー・ケアマネージャー）
              </Box>
              <Box as="li" mb={2} fontSize="lg" color="text.primary" lineHeight="1.8">
                アクティブなアサイン数
              </Box>
              <Box as="li" mb={2} fontSize="lg" color="text.primary" lineHeight="1.8">
                作業完了率
              </Box>
              <Box as="li" mb={2} fontSize="lg" color="text.primary" lineHeight="1.8">
                最近の操作ログ
              </Box>
            </Box>
          </SubSection>
        </VStack>
      ),
    },
    {
      id: 'faq',
      title: 'よくある質問（FAQ）',
      icon: ICONS.faq,
      roles: ['senior', 'helper', 'care_manager', 'system_admin'],
      keywords: ['FAQ', '質問', 'トラブル', 'パスワード', '忘れた', '表示されない', 'エラー', '文字', '小さい'],
      content: (
        <VStack align="stretch" gap={4}>
          <SubSection title="パスワードを忘れてしまいました">
            <Text fontSize="lg" color="text.primary" lineHeight="1.8">
              システム管理者にご連絡ください。管理者がパスワードをリセットし、
              新しいパスワードをお伝えします。QRコードでのログインもご利用いただけます。
            </Text>
          </SubSection>

          <SubSection title="画面が正しく表示されません">
            <Text fontSize="lg" color="text.primary" lineHeight="1.8" mb={2}>
              以下の手順をお試しください：
            </Text>
            <StepList steps={[
              'ブラウザの「更新」ボタン（丸い矢印のマーク）を押します。',
              'それでも直らない場合は、ブラウザを閉じてもう一度開きます。',
              'それでも直らない場合は、別のブラウザ（Chrome、Safariなど）で試します。',
              '問題が続く場合は、システム管理者にご連絡ください。',
            ]} />
          </SubSection>

          <SubSection title="メッセージが届きません">
            <Text fontSize="lg" color="text.primary" lineHeight="1.8">
              メッセージ画面を開いた状態で、ページを更新してみてください。
              インターネット接続が安定していることを確認してください。
              それでも届かない場合は、相手が送信を完了しているか確認してください。
            </Text>
          </SubSection>

          <SubSection title="レシピが保存できません">
            <Text fontSize="lg" color="text.primary" lineHeight="1.8" mb={2}>
              以下を確認してください：
            </Text>
            <Box as="ul" pl={6} listStyleType="disc">
              <Box as="li" mb={2} fontSize="lg" color="text.primary" lineHeight="1.8">
                レシピ名が入力されていますか？（必須項目です）
              </Box>
              <Box as="li" mb={2} fontSize="lg" color="text.primary" lineHeight="1.8">
                カテゴリと種類が選択されていますか？
              </Box>
              <Box as="li" mb={2} fontSize="lg" color="text.primary" lineHeight="1.8">
                インターネットに接続されていますか？
              </Box>
            </Box>
            <Text fontSize="lg" color="text.primary" lineHeight="1.8" mt={2}>
              赤い文字でエラーが表示されている場合は、その指示に従ってください。
            </Text>
          </SubSection>

          <SubSection title="買い物リストが生成されません">
            <Text fontSize="lg" color="text.primary" lineHeight="1.8">
              買い物リストは献立に登録されたレシピから自動生成されます。
              まず献立画面でレシピが正しく設定されているか確認してください。
              レシピに材料が登録されていない場合、リストに反映されません。
            </Text>
          </SubSection>

          <SubSection title="ログインできません">
            <Text fontSize="lg" color="text.primary" lineHeight="1.8" mb={2}>
              以下を確認してください：
            </Text>
            <Box as="ul" pl={6} listStyleType="disc">
              <Box as="li" mb={2} fontSize="lg" color="text.primary" lineHeight="1.8">
                メールアドレスに間違いがないか確認してください。
              </Box>
              <Box as="li" mb={2} fontSize="lg" color="text.primary" lineHeight="1.8">
                パスワードの大文字・小文字が正しいか確認してください。
              </Box>
              <Box as="li" mb={2} fontSize="lg" color="text.primary" lineHeight="1.8">
                キーボードの「Caps Lock」がオフになっているか確認してください。
              </Box>
              <Box as="li" mb={2} fontSize="lg" color="text.primary" lineHeight="1.8">
                それでもログインできない場合は、管理者にパスワードリセットを依頼してください。
              </Box>
            </Box>
          </SubSection>

          <SubSection title="画面の文字が小さくて読みにくいです">
            <Text fontSize="lg" color="text.primary" lineHeight="1.8" mb={3}>
              ブラウザの拡大機能で文字を大きくできます：
            </Text>
            <Box as="ul" pl={6} listStyleType="disc">
              <Box as="li" mb={2} fontSize="lg" color="text.primary" lineHeight="1.8">
                <strong>パソコン</strong>：「Ctrl」キーを押しながら「+」キーを押すと拡大します。
                「Ctrl」+「-」で縮小、「Ctrl」+「0」で元に戻ります。
              </Box>
              <Box as="li" mb={2} fontSize="lg" color="text.primary" lineHeight="1.8">
                <strong>Mac</strong>：「Command」キーを押しながら「+」キーで拡大します。
              </Box>
              <Box as="li" mb={2} fontSize="lg" color="text.primary" lineHeight="1.8">
                <strong>スマートフォン / タブレット</strong>：2本の指で画面を広げる（ピンチアウト）と拡大します。
              </Box>
            </Box>
          </SubSection>

          <SubSection title="「インターネットに接続できません」と表示されます">
            <Text fontSize="lg" color="text.primary" lineHeight="1.8" mb={2}>
              以下をお試しください：
            </Text>
            <StepList steps={[
              'Wi-Fiの電波状況を確認してください。',
              'Wi-Fiを一度オフにして、再度オンにしてみてください。',
              '他のウェブサイト（例：Yahoo! JAPAN）が表示できるか確認してください。',
              'ルーターの電源を抜いて10秒待ち、再度差し込んでみてください。',
              '問題が続く場合は、ご家族やサポート担当者にご相談ください。',
            ]} />
          </SubSection>
        </VStack>
      ),
    },
    {
      id: 'contact',
      title: 'お問い合わせ・サポート',
      icon: ICONS.contact,
      roles: ['senior', 'helper', 'care_manager', 'system_admin'],
      keywords: ['お問い合わせ', 'サポート', '連絡', '電話', 'メール', 'ヘルプ'],
      content: (
        <VStack align="stretch" gap={4}>
          <SubSection title="システムに関するお問い合わせ">
            <Text fontSize="lg" color="text.primary" lineHeight="1.8" mb={3}>
              システムの操作方法やトラブルについてお困りの場合は、以下の方法でサポートを受けられます。
            </Text>
            <Box as="ul" pl={6} listStyleType="disc">
              <Box as="li" mb={3} fontSize="lg" color="text.primary" lineHeight="1.8">
                <strong>システム管理者に連絡</strong><br />
                ログイン問題やアカウントに関する問題は、所属事業所のシステム管理者にご連絡ください。
              </Box>
              <Box as="li" mb={3} fontSize="lg" color="text.primary" lineHeight="1.8">
                <strong>担当ケアマネージャーに相談</strong><br />
                サービス内容に関するご質問は、担当のケアマネージャーにお問い合わせください。
              </Box>
              <Box as="li" mb={3} fontSize="lg" color="text.primary" lineHeight="1.8">
                <strong>担当ヘルパーに相談</strong><br />
                日常的な操作でお困りの場合は、訪問時にヘルパーさんにお声がけください。
              </Box>
            </Box>
          </SubSection>
          <SubSection title="緊急時の対応">
            <Box p={4} bg="danger.50" borderRadius="lg" borderLeft="4px solid" borderColor="danger.500">
              <Text fontSize="lg" color="text.primary" lineHeight="1.8" fontWeight="semibold">
                体調の急変や緊急事態の場合は、このシステムではなく、
                直接電話（119番）でご連絡ください。
              </Text>
            </Box>
          </SubSection>
        </VStack>
      ),
    },
  ], [])
}

// ── Main Help Page Component ────────────────────────────────────────
export default function HelpPage() {
  const user = useAuthStore((state) => state.user)
  const [searchQuery, setSearchQuery] = useState('')
  const sections = useHelpSections()

  // Determine default open sections based on user role
  const defaultOpenSections = useMemo(() => {
    const defaults = ['overview', 'login', 'faq', 'contact']
    if (user?.role) {
      const roleMap: Record<string, string> = {
        senior: 'senior',
        helper: 'helper',
        care_manager: 'care_manager',
        system_admin: 'admin',
      }
      const roleSection = roleMap[user.role]
      if (roleSection) defaults.push(roleSection)
    }
    return defaults
  }, [user?.role])

  // Filter sections by search query
  const filteredSections = useMemo(() => {
    if (!searchQuery.trim()) return sections
    const query = searchQuery.toLowerCase()
    return sections.filter(
      (s) =>
        s.title.toLowerCase().includes(query) ||
        s.keywords.some((k) => k.toLowerCase().includes(query))
    )
  }, [sections, searchQuery])

  const ROLE_LABELS: Record<string, string> = {
    senior: '利用者',
    helper: 'ヘルパー',
    care_manager: 'ケアマネージャー',
    system_admin: '管理者',
  }

  return (
    <Box>
      <PageHeader title="ヘルプ" />

      {/* Role badge + search */}
      <Box
        bg="bg.card"
        borderRadius="2xl"
        border="1px solid"
        borderColor="border.default"
        p={6}
        mb={6}
      >
        <VStack align="stretch" gap={4}>
          <HStack justify="space-between" align="center" flexWrap="wrap" gap={3}>
            <Text fontSize="lg" color="text.primary" lineHeight="1.8">
              このページでは、システムの使い方を説明しています。
              お探しの内容がある場合は、下の検索ボックスをご利用ください。
            </Text>
            {user?.role && (
              <Badge
                bg="brand.50"
                color="brand.700"
                fontSize="md"
                px={4}
                py={2}
                borderRadius="lg"
                fontWeight="semibold"
                flexShrink={0}
              >
                {ROLE_LABELS[user.role] || user.role}
              </Badge>
            )}
          </HStack>
          <Input
            placeholder="キーワードで検索（例：レシピ、ログイン、パスワード）"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            size="lg"
            bg="white"
            borderColor="border.default"
            _hover={{ borderColor: 'border.hover' }}
            _focus={{ borderColor: 'brand.500', boxShadow: '0 0 0 1px var(--chakra-colors-brand-500)' }}
            fontSize="lg"
          />
        </VStack>
      </Box>

      {/* No results */}
      {filteredSections.length === 0 && (
        <Box
          bg="bg.card"
          borderRadius="xl"
          border="1px solid"
          borderColor="border.default"
          p={8}
          textAlign="center"
        >
          <Text fontSize="xl" color="text.muted" mb={2}>
            「{searchQuery}」に一致するヘルプが見つかりませんでした。
          </Text>
          <Text fontSize="lg" color="text.muted">
            別のキーワードで検索するか、お問い合わせセクションをご確認ください。
          </Text>
        </Box>
      )}

      {/* Accordion sections */}
      {filteredSections.length > 0 && (
        <AccordionRoot
          multiple
          defaultValue={searchQuery ? filteredSections.map((s) => s.id) : defaultOpenSections}
        >
          <VStack align="stretch" gap={4}>
            {filteredSections.map((section) => {
              const isRelevant = user?.role ? section.roles.includes(user.role) : true
              return (
                <AccordionItem
                  key={section.id}
                  value={section.id}
                  bg="bg.card"
                  borderRadius="xl"
                  border="1px solid"
                  borderColor={isRelevant ? 'brand.200' : 'border.default'}
                  overflow="hidden"
                >
                  <AccordionItemTrigger
                    px={6}
                    py={5}
                    cursor="pointer"
                    _hover={{ bg: 'brand.50' }}
                    transition="background 0.2s"
                  >
                    <HStack flex="1" gap={3}>
                      <SectionIcon d={section.icon} />
                      <Heading size="lg" color="text.primary" fontWeight="semibold">
                        {section.title}
                      </Heading>
                      {isRelevant && user?.role && !['overview', 'login', 'faq', 'contact'].includes(section.id) && (
                        <Badge
                          bg="brand.50"
                          color="brand.600"
                          fontSize="sm"
                          px={2}
                          py={0.5}
                          borderRadius="md"
                        >
                          あなた向け
                        </Badge>
                      )}
                    </HStack>
                    <ChevronIcon />
                  </AccordionItemTrigger>
                  <AccordionItemContent>
                    <AccordionItemBody px={6} pb={6} pt={2}>
                      {section.content}
                    </AccordionItemBody>
                  </AccordionItemContent>
                </AccordionItem>
              )
            })}
          </VStack>
        </AccordionRoot>
      )}

      {/* Footer */}
      <Box mt={8} textAlign="center">
        <Text fontSize="md" color="text.muted">
          ヘルパー管理システム ヘルプ
        </Text>
      </Box>
    </Box>
  )
}
