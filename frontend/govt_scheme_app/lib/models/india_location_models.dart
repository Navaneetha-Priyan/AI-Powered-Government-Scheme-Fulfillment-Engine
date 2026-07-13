class IndiaLocations {
  IndiaLocations({
    required this.states,
    required this.districtsByState,
  });

  final List<String> states;
  final Map<String, List<String>> districtsByState;

  factory IndiaLocations.fromJson(Map<String, dynamic> json) {
    final rawStates = (json['states'] as List<dynamic>? ?? const [])
        .map((value) => value.toString())
        .where((value) => value.trim().isNotEmpty)
        .toList();

    final rawDistricts = <String, List<String>>{};
    final districtsByStateJson = json['districts_by_state'];
    if (districtsByStateJson is Map<String, dynamic>) {
      for (final entry in districtsByStateJson.entries) {
        final districts = (entry.value as List<dynamic>? ?? const [])
            .map((value) => value.toString())
            .where((value) => value.trim().isNotEmpty)
            .toList();
        rawDistricts[entry.key.toString()] = districts;
      }
    }

    return IndiaLocations(
      states: rawStates,
      districtsByState: rawDistricts,
    );
  }

  static IndiaLocations fallback() {
    return IndiaLocations(
      states: const [
        'Andaman and Nicobar Islands',
        'Andhra Pradesh',
        'Arunachal Pradesh',
        'Assam',
        'Bihar',
        'Chandigarh',
        'Chhattisgarh',
        'Dadra and Nagar Haveli and Daman and Diu',
        'Delhi',
        'Goa',
        'Gujarat',
        'Haryana',
        'Himachal Pradesh',
        'Jammu and Kashmir',
        'Jharkhand',
        'Karnataka',
        'Kerala',
        'Ladakh',
        'Lakshadweep',
        'Madhya Pradesh',
        'Maharashtra',
        'Manipur',
        'Meghalaya',
        'Mizoram',
        'Nagaland',
        'Odisha',
        'Puducherry',
        'Punjab',
        'Rajasthan',
        'Sikkim',
        'Tamil Nadu',
        'Telangana',
        'Tripura',
        'Uttar Pradesh',
        'Uttarakhand',
        'West Bengal',
      ],
      districtsByState: const {},
    );
  }
}