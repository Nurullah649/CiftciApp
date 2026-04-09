import React from 'react';
import {
  ActivityIndicator,
  StyleProp,
  StyleSheet,
  Text,
  TextStyle,
  TouchableOpacity,
  View,
  ViewStyle,
} from 'react-native';
import { theme } from '../theme/theme';

type Props = {
  label: string;
  onPress: () => void;
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
  disabled?: boolean;
  loading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  style?: StyleProp<ViewStyle>;
  labelStyle?: StyleProp<TextStyle>;
};

export function AppButton({
  label,
  onPress,
  variant = 'primary',
  disabled = false,
  loading = false,
  leftIcon,
  rightIcon,
  style,
  labelStyle,
}: Props) {
  const visual = BUTTONS[variant];
  const isDisabled = disabled || loading;

  return (
    <TouchableOpacity
      activeOpacity={0.88}
      onPress={onPress}
      disabled={isDisabled}
      style={[
        styles.base,
        visual.container,
        isDisabled && styles.disabled,
        style,
      ]}
    >
      {loading ? (
        <ActivityIndicator color={visual.text.color as string} />
      ) : (
        <View style={styles.content}>
          {leftIcon}
          <Text style={[styles.label, visual.text, labelStyle]}>{label}</Text>
          {rightIcon}
        </View>
      )}
    </TouchableOpacity>
  );
}

const BUTTONS = {
  primary: {
    container: {
      backgroundColor: theme.accent,
      borderColor: theme.accent,
    },
    text: {
      color: '#FFFFFF',
    },
  },
  secondary: {
    container: {
      backgroundColor: theme.surface,
      borderColor: theme.border,
    },
    text: {
      color: theme.ink,
    },
  },
  ghost: {
    container: {
      backgroundColor: theme.surfaceMuted,
      borderColor: 'transparent',
    },
    text: {
      color: theme.inkSecondary,
    },
  },
  danger: {
    container: {
      backgroundColor: theme.dangerSoft,
      borderColor: theme.dangerSoft,
    },
    text: {
      color: theme.danger,
    },
  },
} as const;

const styles = StyleSheet.create({
  base: {
    minHeight: 52,
    borderRadius: theme.radiusMd,
    borderWidth: 1,
    paddingHorizontal: 18,
    justifyContent: 'center',
    alignItems: 'center',
  },
  content: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
  },
  label: {
    fontSize: 15,
    fontWeight: '800',
    letterSpacing: 0.1,
  },
  disabled: {
    opacity: 0.5,
  },
});
