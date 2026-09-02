import { useContext } from 'react';
import PreferencesContext from '../context/PreferencesContext';

export default function usePreferences() {
  return useContext(PreferencesContext);
}
