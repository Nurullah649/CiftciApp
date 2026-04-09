import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity, StatusBar } from 'react-native';
import { ArrowLeft } from 'lucide-react-native';
import { theme } from '../theme/theme';

type Props = {
  title: string;
  onBack: () => void;
  right?: React.ReactNode;
  eyebrow?: string;
};

export function StackHeader({ title, onBack, right, eyebrow = 'ÇİFTÇİ APP' }: Props) {
  return (
    <>
      <StatusBar barStyle="dark-content" backgroundColor={theme.bg} />
      <View style={styles.wrap}>
        <TouchableOpacity onPress={onBack} style={styles.back} hitSlop={12}>
          <ArrowLeft size={20} color={theme.ink} />
        </TouchableOpacity>
        <View style={styles.titleWrap}>
          <Text style={styles.eyebrow}>{eyebrow}</Text>
          <Text style={styles.title} numberOfLines={1}>
            {title}
          </Text>
        </View>
        <View style={styles.right}>{right ?? <View style={styles.rightSpacer} />}</View>
      </View>
    </>
  );
}

const styles = StyleSheet.create({
  wrap: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingTop: 8,
    paddingBottom: 12,
    backgroundColor: theme.bg,
  },
  back: {
    width: 46,
    height: 46,
    borderRadius: 16,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 10,
    borderWidth: 1,
    borderColor: theme.border,
    backgroundColor: theme.surface,
  },
  titleWrap: { flex: 1 },
  eyebrow: {
    color: theme.muted,
    fontSize: 10,
    fontWeight: '900',
    letterSpacing: 1.6,
    marginBottom: 3,
  },
  title: { fontSize: 22, fontWeight: '900', color: theme.ink },
  right: { minWidth: 44, alignItems: 'flex-end', justifyContent: 'center' },
  rightSpacer: { width: 44 },
});
