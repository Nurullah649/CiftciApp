import React, { useState, useEffect } from 'react';
import { View, ActivityIndicator, StyleSheet, Platform } from 'react-native';
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

function MainTabs() {
  return (
    <Tab.Navigator
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: theme.tabActive,
        tabBarInactiveTintColor: theme.tabInactive,
        tabBarStyle: {
          position: 'absolute',
          left: 16,
          right: 16,
          bottom: Platform.OS === 'ios' ? 28 : 16,
          height: 64,
          paddingBottom: 10,
          paddingTop: 10,
          backgroundColor: theme.tabBarBg,
          borderTopWidth: 0,
          borderRadius: 20,
          elevation: 24,
          shadowColor: '#000',
          shadowOffset: { width: 0, height: 10 },
          shadowOpacity: 0.28,
          shadowRadius: 20,
        },
        tabBarLabelStyle: { fontSize: 10, fontWeight: '800', letterSpacing: 0.4 },
        tabBarItemStyle: { paddingVertical: 2 },
      }}
    >
      <Tab.Screen
        name="Dashboard"
        component={DashboardScreen}
        options={{
          tabBarLabel: 'Özet',
          tabBarIcon: ({ color, focused }) => <Sprout size={22} color={color} strokeWidth={focused ? 2.5 : 2} />,
        }}
      />
      <Tab.Screen
        name="Schedule"
        component={ScheduleScreen}
        options={{
          tabBarLabel: 'Takvim',
          tabBarIcon: ({ color, focused }) => <CalendarRange size={22} color={color} strokeWidth={focused ? 2.5 : 2} />,
        }}
      />
      <Tab.Screen
        name="Analysis"
        component={AnalysisScreen}
        options={{
          tabBarLabel: 'Tarla',
          tabBarIcon: ({ color, focused }) => <Leaf size={22} color={color} strokeWidth={focused ? 2.5 : 2} />,
        }}
      />
      <Tab.Screen
        name="Chat"
        component={ChatScreen}
        options={{
          tabBarLabel: 'Asistan',
          tabBarIcon: ({ color, focused }) => <MessageCircle size={22} color={color} strokeWidth={focused ? 2.5 : 2} />,
        }}
      />
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
    backgroundColor: theme.forest,
    justifyContent: 'center',
    alignItems: 'center',
  },
  splashInner: {
    width: 96,
    height: 96,
    borderRadius: 28,
    borderWidth: 3,
    borderColor: theme.tabActive,
    backgroundColor: 'rgba(217,249,157,0.08)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  splashFoot: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    height: 120,
    backgroundColor: theme.bg,
    borderTopLeftRadius: 40,
    borderTopRightRadius: 40,
  },
});
