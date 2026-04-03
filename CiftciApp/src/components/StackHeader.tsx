import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity, StatusBar } from 'react-native';
import { ArrowLeft } from 'lucide-react-native';
import { theme } from '../theme/theme';

type Props = {
  title: string;
  onBack: () => void;
  right?: React.ReactNode;
};

export function StackHeader({ title, onBack, right }: Props) {
  return (
    <>
      <StatusBar barStyle="light-content" backgroundColor={theme.forest} />
      <View style={styles.wrap}>
        <TouchableOpacity onPress={onBack} style={styles.back} hitSlop={12}>
          <ArrowLeft size={22} color="#fff" />
        </TouchableOpacity>
        <Text style={styles.title} numberOfLines={1}>
          {title}
        </Text>
        <View style={styles.right}>{right ?? <View style={styles.rightSpacer} />}</View>
      </View>
    </>
  );
}

const styles = StyleSheet.create({
  wrap: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingVertical: 12,
    backgroundColor: theme.forest,
    borderBottomLeftRadius: theme.radiusMd,
    borderBottomRightRadius: theme.radiusMd,
  },
  back: { padding: 10, marginRight: 4 },
  title: { flex: 1, fontSize: 18, fontWeight: '800', color: '#fff' },
  right: { minWidth: 44, alignItems: 'flex-end', justifyContent: 'center' },
  rightSpacer: { width: 44 },
});
