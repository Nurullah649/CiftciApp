import React from 'react';
import { StyleSheet, View } from 'react-native';
import { theme } from '../theme/theme';

type Props = {
  tone?: 'sand' | 'forest';
};

export function AmbientBackdrop({ tone = 'sand' }: Props) {
  const isForest = tone === 'forest';

  return (
    <View pointerEvents="none" style={StyleSheet.absoluteFill}>
      <View
        style={[
          styles.orb,
          styles.orbTop,
          { backgroundColor: isForest ? 'rgba(255,255,255,0.04)' : 'rgba(31,77,59,0.04)' },
        ]}
      />
      <View
        style={[
          styles.orb,
          styles.orbRight,
          { backgroundColor: isForest ? 'rgba(111,168,131,0.07)' : 'rgba(111,168,131,0.05)' },
        ]}
      />
      <View
        style={[
          styles.orb,
          styles.orbBottom,
          { backgroundColor: isForest ? 'rgba(255,255,255,0.03)' : 'rgba(62,111,142,0.04)' },
        ]}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  orb: {
    position: 'absolute',
    borderRadius: 999,
  },
  orbTop: {
    top: -90,
    left: -60,
    width: 260,
    height: 260,
  },
  orbRight: {
    top: 120,
    right: -90,
    width: 240,
    height: 240,
  },
  orbBottom: {
    bottom: -120,
    left: '10%',
    width: 320,
    height: 320,
  },
});
