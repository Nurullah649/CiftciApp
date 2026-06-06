import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { ArrowLeft } from 'lucide-react-native';
import { colors, typography, spacing } from '../../theme';

type Props = {
  title: string;
  subtitle?: string;
  onBack: () => void;
  right?: React.ReactNode;
};

export function StackHeader({ title, subtitle, onBack, right }: Props) {
  return (
    <View style={styles.wrap}>
      <TouchableOpacity onPress={onBack} style={styles.back} activeOpacity={0.7}>
        <ArrowLeft size={22} color={colors.text} />
      </TouchableOpacity>
      <View style={styles.center}>
        <Text style={styles.title}>{title}</Text>
        {subtitle ? <Text style={styles.sub}>{subtitle}</Text> : null}
      </View>
      <View style={styles.right}>{right ?? <View style={{ width: 40 }} />}</View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.md,
    backgroundColor: colors.surface,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderLight,
  },
  back: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: colors.bg,
    alignItems: 'center',
    justifyContent: 'center',
  },
  center: { flex: 1, marginHorizontal: spacing.sm },
  title: { ...typography.h2, color: colors.text },
  sub: { ...typography.caption, color: colors.textMuted, marginTop: 2 },
  right: { minWidth: 40, alignItems: 'flex-end' },
});
