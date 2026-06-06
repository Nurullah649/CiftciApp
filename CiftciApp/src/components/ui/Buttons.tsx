import React from 'react';
import {
  TouchableOpacity,
  Text,
  StyleSheet,
  ActivityIndicator,
  ViewStyle,
  TextStyle,
} from 'react-native';
import { colors, radius, typography, shadow } from '../../theme';

type BtnProps = {
  label: string;
  onPress: () => void;
  loading?: boolean;
  disabled?: boolean;
  icon?: React.ReactNode;
  style?: ViewStyle;
  textStyle?: TextStyle;
};

export function PrimaryButton({ label, onPress, loading, disabled, icon, style }: BtnProps) {
  return (
    <TouchableOpacity
      style={[styles.primary, (disabled || loading) && styles.primaryDisabled, style]}
      onPress={onPress}
      disabled={disabled || loading}
      activeOpacity={0.85}
    >
      {loading ? (
        <ActivityIndicator color={colors.textOnPrimary} />
      ) : (
        <>
          {icon}
          <Text style={styles.primaryText}>{label}</Text>
        </>
      )}
    </TouchableOpacity>
  );
}

export function SecondaryButton({ label, onPress, loading, disabled, icon, style }: BtnProps) {
  return (
    <TouchableOpacity
      style={[styles.secondary, style]}
      onPress={onPress}
      disabled={disabled || loading}
      activeOpacity={0.85}
    >
      {loading ? (
        <ActivityIndicator color={colors.primary} />
      ) : (
        <>
          {icon}
          <Text style={styles.secondaryText}>{label}</Text>
        </>
      )}
    </TouchableOpacity>
  );
}

export function GhostButton({ label, onPress, style, textStyle }: BtnProps) {
  return (
    <TouchableOpacity style={[styles.ghost, style]} onPress={onPress} activeOpacity={0.7}>
      <Text style={[styles.ghostText, textStyle]}>{label}</Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  primary: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
    backgroundColor: colors.primary,
    paddingVertical: 18,
    paddingHorizontal: 24,
    borderRadius: radius.md,
    ...shadow.soft,
  },
  primaryDisabled: { backgroundColor: colors.primaryLight, opacity: 0.7 },
  primaryText: { color: colors.textOnPrimary, ...typography.h3, fontSize: 16 },
  secondary: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
    backgroundColor: colors.surface,
    paddingVertical: 18,
    paddingHorizontal: 24,
    borderRadius: radius.md,
    borderWidth: 2,
    borderColor: colors.primary,
  },
  secondaryText: { color: colors.primary, ...typography.h3, fontSize: 16 },
  ghost: { padding: 14, alignItems: 'center' },
  ghostText: { color: colors.textSecondary, fontWeight: '600', fontSize: 15 },
});
