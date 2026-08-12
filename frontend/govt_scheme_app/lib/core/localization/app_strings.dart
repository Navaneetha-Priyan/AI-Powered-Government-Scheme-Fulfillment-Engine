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
  static const loginAgain = 'Your session has expired. Please sign in again.';
  static const somethingWrong = 'Something went wrong. Please try again.';

  static String friendlyError(Object error) {
    final text = error.toString().replaceFirst('Exception: ', '').trim();
    final lower = text.toLowerCase();

    // Auth errors
    if (lower.contains('401') ||
        lower.contains('unauthorized') ||
        lower.contains('token expired') ||
        lower.contains('invalid token')) {
      return loginAgain;
    }

    // Network errors
    if (lower.contains('socket') ||
        lower.contains('network') ||
        lower.contains('connection') ||
        lower.contains('timeout') ||
        lower.contains('unable to reach') ||
        lower.contains('connection reset') ||
        lower.contains('host lookup')) {
      return checkInternet;
    }

    // Document errors
    if (lower.contains('unsupported_document_type') ||
        lower.contains('unsupported document type')) {
      return 'This document type is not supported yet. Please try a different document.';
    }
    if (lower.contains('file_too_large') ||
        lower.contains('file must be') ||
        lower.contains('413')) {
      return 'The file is too large. Please use a smaller file (under 10 MB).';
    }
    if (lower.contains('invalid_document') ||
        lower.contains('422') ||
        lower.contains('unprocessable')) {
      return 'Please upload a valid PDF or image file (JPG, JPEG, PNG).';
    }

    // Profile errors
    if (lower.contains('profile_review_required') ||
        lower.contains('profile review required')) {
      return 'Please review and resolve all conflicts before confirming your profile.';
    }
    if (lower.contains('document_not_found') ||
        lower.contains('not found') ||
        lower.contains('404')) {
      return 'The requested information was not found.';
    }

    // Server errors
    if (lower.contains('500') ||
        lower.contains('internal_server_error') ||
        lower.contains('internal server error')) {
      return 'The server encountered an error. Please try again in a moment.';
    }

    // Generic fallback
    if (text.isEmpty || lower.contains('dioexception')) {
      return somethingWrong;
    }

    return text;
  }
}
