import React from 'react';
import { StyleSheet, ViewStyle } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { colors } from '../../theme';

type Props = {
  children: React.ReactNode;
  edges?: ('top' | 'bottom' | 'left' | 'right')[];
  style?: ViewStyle;
  variant?: 'default' | 'cream' | 'dark';
};

export function Screen({ children, edges = ['top', 'left', 'right'], style, variant = 'cream' }: Props) {
  const bg =
    variant === 'dark' ? colors.primaryDark : variant === 'default' ? colors.bg : colors.bg;
  return (
    <SafeAreaView style={[styles.base, { backgroundColor: bg }, style]} edges={edges}>
      {children}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  base: { flex: 1 },
});
