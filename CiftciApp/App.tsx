import React, { useState, useEffect } from 'react';
import { View, ActivityIndicator, StyleSheet, Platform, Text } from 'react-native';
import { NavigationContainer, DefaultTheme, Theme } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { Sprout, Leaf, MessageCircle, CalendarRange } from 'lucide-react-native';
import * as Notifications from 'expo-notifications';
import { isLoggedIn } from './src/services/apiService';
import { theme } from './src/theme/theme';

import LoginScreen from './src/screens/LoginScreen';
import RegisterScreen from './src/screens/RegisterScreen';
import DashboardScreen from './src/screens/DashboardScreen';
import ChatScreen from './src/screens/ChatScreen';
import AnalysisScreen from './src/screens/AnalysisScreen';
import NotificationsScreen from './src/screens/NotificationsScreen';
import ChatHistoryScreen from './src/screens/ChatHistoryScreen';
import ProfileScreen from './src/screens/ProfileScreen';
import ScheduleScreen from './src/screens/ScheduleScreen';
import MapScreen from './src/screens/MapScreen';

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowBanner: true,
    shouldShowList: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
  }),
});

const navTheme: Theme = {
  ...DefaultTheme,
  dark: false,
  colors: {
    ...DefaultTheme.colors,
    primary: theme.forestLight,
    background: theme.bg,
    card: theme.surface,
    text: theme.ink,
    border: theme.border,
    notification: theme.accent,
  },
};

const Stack = createNativeStackNavigator();
const Tab = createBottomTabNavigator();
const TAB_META = {
  Dashboard: { label: 'Merkez', icon: Sprout },
  Schedule: { label: 'Plan', icon: CalendarRange },
  Analysis: { label: 'Tarla', icon: Leaf },
  Chat: { label: 'Asistan', icon: MessageCircle },
} as const;

function MainTabs() {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => {
        const meta = TAB_META[route.name as keyof typeof TAB_META];
        const isPrimary = route.name === 'Analysis';

        return {
          headerShown: false,
          tabBarShowLabel: false,
          tabBarHideOnKeyboard: true,
          sceneStyle: { backgroundColor: theme.bg },
          tabBarStyle: {
            position: 'absolute',
            left: 18,
            right: 18,
            bottom: Platform.OS === 'ios' ? 26 : 16,
            height: 74,
            paddingHorizontal: 10,
            paddingBottom: 10,
            paddingTop: 10,
            backgroundColor: theme.tabBarBg,
            borderTopWidth: 1,
            borderTopColor: theme.border,
            borderRadius: 24,
            elevation: 0,
            shadowColor: theme.shadowStrong,
            shadowOffset: { width: 0, height: 10 },
            shadowOpacity: 1,
            shadowRadius: 20,
          },
          tabBarItemStyle: { paddingVertical: 2 },
          tabBarIcon: ({ focused }) => {
            const Icon = meta.icon;
            const textColor = focused ? theme.tabActive : theme.tabInactive;

            return (
              <View
                style={[
                  styles.tabItem,
                  focused && styles.tabItemActive,
                ]}
              >
                <Icon size={focused ? 19 : 18} color={textColor} strokeWidth={focused ? 2.4 : 2} />
                {focused && <Text style={[styles.tabLabel, { color: textColor }]}>{meta.label}</Text>}
              </View>
            );
          },
        };
      }}
    >
      <Tab.Screen name="Dashboard" component={DashboardScreen} />
      <Tab.Screen name="Schedule" component={ScheduleScreen} />
      <Tab.Screen name="Analysis" component={AnalysisScreen} />
      <Tab.Screen name="Chat" component={ChatScreen} />
    </Tab.Navigator>
  );
}

export default function App() {
  const [initialRoute, setInitialRoute] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const loggedIn = await isLoggedIn();
        setInitialRoute(loggedIn ? 'Main' : 'Login');
      } catch {
        setInitialRoute('Login');
      }
    })();
  }, []);

  if (!initialRoute) {
    return (
      <View style={styles.splash}>
        <View style={styles.splashInner}>
          <ActivityIndicator size="large" color={theme.tabActive} />
        </View>
        <View style={styles.splashFoot} />
      </View>
    );
  }

  return (
    <NavigationContainer theme={navTheme}>
      <Stack.Navigator screenOptions={{ headerShown: false }} initialRouteName={initialRoute}>
        <Stack.Screen name="Login" component={LoginScreen} />
        <Stack.Screen name="Register" component={RegisterScreen} />
        <Stack.Screen name="Main" component={MainTabs} />
        <Stack.Screen name="Notifications" component={NotificationsScreen} />
        <Stack.Screen name="ChatHistory" component={ChatHistoryScreen} />
        <Stack.Screen name="Profile" component={ProfileScreen} />
        <Stack.Screen name="Map" component={MapScreen} />
      </Stack.Navigator>
    </NavigationContainer>
  );
}

const styles = StyleSheet.create({
  splash: {
    flex: 1,
    backgroundColor: theme.bg,
    justifyContent: 'center',
    alignItems: 'center',
  },
  splashInner: {
    width: 112,
    height: 112,
    borderRadius: 34,
    borderWidth: 1,
    borderColor: theme.border,
    backgroundColor: theme.surface,
    justifyContent: 'center',
    alignItems: 'center',
  },
  splashFoot: {
    display: 'none',
  },
  tabItem: {
    minWidth: 56,
    height: 50,
    borderRadius: 16,
    paddingHorizontal: 12,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
  tabItemActive: {
    backgroundColor: theme.accentSoft,
  },
  tabLabel: {
    fontSize: 12,
    fontWeight: '900',
    letterSpacing: 0.3,
  },
});
