import React, { useState, useEffect } from 'react';
import { View, ActivityIndicator, StyleSheet } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { Home, ScanLine, MessageSquare } from 'lucide-react-native';
import * as Notifications from 'expo-notifications';
import { isLoggedIn } from './src/services/apiService';

// Ekranları Import Et
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

// Bildirim Ayarları
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowBanner: true,
    shouldShowList: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
  }),
});

const Stack = createNativeStackNavigator();
const Tab = createBottomTabNavigator();

function MainTabs() {
  return (
    <Tab.Navigator
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: '#16a34a',
        tabBarStyle: { height: 65, paddingBottom: 10, paddingTop: 10 }
      }}
    >
      <Tab.Screen
        name="Dashboard"
        component={DashboardScreen}
        options={{
          tabBarLabel: 'Ana Sayfa',
          tabBarIcon: ({ color }) => <Home size={24} color={color} />
        }}
      />
      <Tab.Screen
        name="Analysis"
        component={AnalysisScreen}
        options={{
          tabBarLabel: 'Analiz',
          tabBarIcon: ({ color }) => <ScanLine size={24} color={color} />
        }}
      />
      <Tab.Screen
        name="Chat"
        component={ChatScreen}
        options={{
          tabBarLabel: 'Asistan',
          tabBarIcon: ({ color }) => <MessageSquare size={24} color={color} />
        }}
      />
    </Tab.Navigator>
  );
}

export default function App() {
  const [initialRoute, setInitialRoute] = useState<string | null>(null);

  useEffect(() => {
    checkAuthStatus();
  }, []);

  const checkAuthStatus = async () => {
    try {
      const loggedIn = await isLoggedIn();
      setInitialRoute(loggedIn ? 'Main' : 'Login');
    } catch (error) {
      setInitialRoute('Login');
    }
  };

  // Splash / Loading ekranı
  if (!initialRoute) {
    return (
      <View style={styles.splash}>
        <ActivityIndicator size="large" color="#16a34a" />
      </View>
    );
  }

  return (
    <NavigationContainer>
      <Stack.Navigator screenOptions={{ headerShown: false }} initialRouteName={initialRoute}>
        <Stack.Screen name="Login" component={LoginScreen} />
        <Stack.Screen name="Register" component={RegisterScreen} />
        <Stack.Screen name="Main" component={MainTabs} />
        <Stack.Screen name="Notifications" component={NotificationsScreen} />
        <Stack.Screen name="ChatHistory" component={ChatHistoryScreen} />
        <Stack.Screen name="Profile" component={ProfileScreen} />
        <Stack.Screen name="Schedule" component={ScheduleScreen} />
        <Stack.Screen name="Map" component={MapScreen} />
      </Stack.Navigator>
    </NavigationContainer>
  );
}

const styles = StyleSheet.create({
  splash: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#f9fafb',
  },
});
