class AppStrings {
  AppStrings._();

  static const appName = 'Government Services';
  static const signIn = 'Sign In';
  static const createAccount = 'Create Account';
  static const continueText = 'Continue';
  static const back = 'Back';
  static const retry = 'Try Again';
  static const home = 'Home';
  static const myInformation = 'My Information';
  static const myProfile = 'My Profile';
  static const myDocuments = 'My Documents';
  static const myLand = 'My Land';
  static const incomeDetails = 'Income Details';
  static const updateRecords = 'Update My Records';
  static const settings = 'Settings';
  static const loadingInformation = 'Loading your information...';
  static const loadingDocuments = 'Loading your documents...';
  static const loadingLand = 'Loading your land details...';
  static const updatingRecords = 'Updating your records...';
  static const checkInternet = 'Please check your internet connection.';
  static const loginAgain = 'Please log in again.';
  static const somethingWrong = 'Something went wrong. Please try again.';

  static String friendlyError(Object error) {
    final text = error.toString().replaceFirst('Exception: ', '').trim();
    final lower = text.toLowerCase();

    if (lower.contains('401') ||
        lower.contains('unauthorized') ||
        lower.contains('token')) {
      return loginAgain;
    }
    if (lower.contains('socket') ||
        lower.contains('network') ||
        lower.contains('connection') ||
        lower.contains('timeout') ||
        lower.contains('unable to reach')) {
      return checkInternet;
    }
    if (lower.contains('not found')) {
      return 'The information was not found.';
    }
    if (text.isEmpty || lower.contains('dioexception')) {
      return somethingWrong;
    }
    return text;
  }
}
