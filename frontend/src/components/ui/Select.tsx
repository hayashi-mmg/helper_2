import { NativeSelectRoot, NativeSelectField, NativeSelectIndicator } from '@chakra-ui/react'

interface SelectOption {
  value: string
  label: string
}

interface SelectProps {
  value: string
  onChange: (value: string) => void
  options: SelectOption[]
  placeholder?: string
  size?: 'sm' | 'md' | 'lg'
}

export default function Select({ value, onChange, options, placeholder, size = 'lg' }: SelectProps) {
  return (
    <NativeSelectRoot size={size}>
      <NativeSelectField
        value={value}
        onChange={(e) => onChange(e.target.value)}
        fontSize="md"
        cursor="pointer"
      >
        {placeholder && <option value="">{placeholder}</option>}
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>{opt.label}</option>
        ))}
      </NativeSelectField>
      <NativeSelectIndicator />
    </NativeSelectRoot>
  )
}
